import asyncio
import hashlib
import json
import logging
import os
import re
import sqlite3
import tempfile
from datetime import timedelta
from pathlib import Path

import discord
from discord.ext import tasks
from nudenet import NudeDetector
from PIL import Image

CHANNEL_ID = 1560149527984476180
MOD_LOG_ID = 1560149552168837181
INTERVAL_MINUTES = 10
NUDITY_THRESHOLD = 0.65
MAX_MEDIA_BYTES = 25 * 1024 * 1024
MAX_FRAMES = 120

BLOCKED_CLASSES = {
    'FEMALE_BREAST_EXPOSED',
    'FEMALE_GENITALIA_EXPOSED',
    'MALE_GENITALIA_EXPOSED',
    'ANUS_EXPOSED',
    'BUTTOCKS_EXPOSED',
}

EXPLICIT_TEXT_PATTERNS = (
    r'\b(?:send|show)(?: me| us)? (?:your )?(?:nudes|dick pics?|pussy pics?|tits)\b',
    r'\b(?:suck|lick)(?: on)? (?:my|your|his|her) (?:dick|cock|pussy|clit)\b',
    r'\b(?:fuck me|fuck my|cum on my|cum in my|cum inside me)\b',
    r'\b(?:watch|free|hardcore) porn\b',
    r'\b(?:buy|selling|sell) (?:my )?(?:nudes|sex videos)\b',
)

STATE_PATH = Path(os.getenv('STATE_PATH', './data/moderation.sqlite3'))
STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('moderation')


class Moderator(discord.Client):
    def __init__(self):
        intents = discord.Intents.none()
        intents.guilds = True
        intents.guild_messages = True
        intents.message_content = True

        super().__init__(
            intents=intents,
            max_messages=None,
            allowed_mentions=discord.AllowedMentions.none(),
        )

        self.db = sqlite3.connect(STATE_PATH)

        self.db.execute(
            'CREATE TABLE IF NOT EXISTS checked '
            '(id INTEGER PRIMARY KEY, digest TEXT)'
        )
        self.db.execute(
            'CREATE TABLE IF NOT EXISTS pending '
            '(id INTEGER PRIMARY KEY)'
        )
        self.db.execute(
            'CREATE TABLE IF NOT EXISTS settings '
            '(key TEXT PRIMARY KEY, value TEXT)'
        )
        self.db.execute(
            'CREATE TABLE IF NOT EXISTS outbox '
            '(id INTEGER PRIMARY KEY, body TEXT)'
        )
        self.db.commit()

        self.detector = None

    async def setup_hook(self):
        self.scanner.start()

    async def close(self):
        self.scanner.cancel()
        self.db.close()
        await super().close()

    async def on_raw_message_edit(self, payload):
        if payload.channel_id == CHANNEL_ID:
            self.db.execute(
                'INSERT OR IGNORE INTO pending VALUES (?)',
                (payload.message_id,),
            )
            self.db.commit()

    async def frames(self, attachment, directory):
        if attachment.size > MAX_MEDIA_BYTES:
            raise ValueError('Media exceeds the 25 MiB scan limit')

        source = directory / 'source'
        await attachment.save(source)

        image_extensions = {
            '.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp'
        }

        if (
            (attachment.content_type or '').startswith('image/')
            or Path(attachment.filename).suffix.lower() in image_extensions
        ):
            with Image.open(source) as opened:
                if not getattr(opened, 'is_animated', False):
                    opened.thumbnail((1280, 1280))
                    target = directory / 'frame-0001.jpg'
                    opened.convert('RGB').save(target)
                    return [target]

        process = await asyncio.create_subprocess_exec(
            'ffmpeg',
            '-nostdin',
            '-hide_banner',
            '-loglevel',
            'error',
            '-protocol_whitelist',
            'file,pipe',
            '-i',
            str(source),
            '-vf',
            'fps=1,scale=640:640:force_original_aspect_ratio=decrease',
            '-frames:v',
            str(MAX_FRAMES),
            str(directory / 'frame-%04d.jpg'),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        try:
            await asyncio.wait_for(process.wait(), timeout=60)
        except BaseException:
            if process.returncode is None:
                process.kill()
                await process.wait()
            raise

        images = sorted(directory.glob('frame-*.jpg'))

        if process.returncode != 0 or not images:
            raise ValueError('Media could not be decoded')

        return images

    def detect(self, image):
        if self.detector is None:
            self.detector = NudeDetector()

        return any(
            item['class'] in BLOCKED_CLASSES
            and item['score'] >= NUDITY_THRESHOLD
            for item in self.detector.detect(str(image))
        )

    async def classify(self, message):
        text = '\n'.join(
            [message.content]
            + [
                '\n'.join(
                    filter(
                        None,
                        [embed.title, embed.description]
                        + [
                            f'{field.name}: {field.value}'
                            for field in embed.fields
                        ],
                    )
                )
                for embed in message.embeds
            ]
        )

        normalized = re.sub(r'[^a-z0-9\s]', ' ', text.casefold())
        normalized = re.sub(r'\s+', ' ', normalized)

        if any(
            re.search(pattern, normalized)
            for pattern in EXPLICIT_TEXT_PATTERNS
        ):
            return 'Explicit sexual phrase detected', []

        limitations = []

        for attachment in message.attachments:
            content_type = attachment.content_type or ''
            extension = Path(attachment.filename).suffix.lower()

            supported = (
                content_type.startswith(('image/', 'video/'))
                or extension in {
                    '.png', '.jpg', '.jpeg', '.webp', '.gif',
                    '.bmp', '.mp4', '.mov', '.webm', '.mkv',
                }
            )

            if not supported:
                limitations.append('Unsupported attachment type')
                continue

            with tempfile.TemporaryDirectory() as temp:
                images = await self.frames(attachment, Path(temp))

                for image in images:
                    if await asyncio.to_thread(self.detect, image):
                        return 'Nudity detected in attached media', []

                if len(images) >= MAX_FRAMES:
                    limitations.append(
                        'Media reached the 120-frame scan limit'
                    )

        if any(
            embed.image or embed.thumbnail or embed.video
            for embed in message.embeds
        ):
            limitations.append('Externally linked media is not scanned')

        return None, limitations

    async def process(self, channel, message):
        if message.author.id == self.user.id:
            self.db.execute(
                'DELETE FROM pending WHERE id=?',
                (message.id,),
            )
            self.db.commit()
            return

        digest = hashlib.sha256(
            json.dumps(
                {
                    'text': message.content,
                    'files': [
                        (a.id, a.filename, a.size)
                        for a in message.attachments
                    ],
                    'embeds': [
                        embed.to_dict()
                        for embed in message.embeds
                    ],
                    'edit': str(message.edited_at),
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()

        old = self.db.execute(
            'SELECT digest FROM checked WHERE id=?',
            (message.id,),
        ).fetchone()

        if old and old[0] == digest:
            self.db.execute(
                'DELETE FROM pending WHERE id=?',
                (message.id,),
            )
            self.db.commit()
            return

        reason, limitations = await self.classify(message)

        if reason:
            latest = await channel.fetch_message(message.id)

            if latest.edited_at != message.edited_at:
                raise RuntimeError(
                    'Message changed during scan; will retry'
                )

            await latest.delete(reason=reason)

            body = (
                f'Deleted message: {message.id}\n'
                f'User ID: {message.author.id}\n'
                f'Channel: <#{CHANNEL_ID}>\n'
                f'Reason: {reason}'
            )

            self.db.execute(
                'INSERT OR REPLACE INTO outbox VALUES (?,?)',
                (message.id, body),
            )

        elif limitations:
            logger.warning(
                'Message %s: %s',
                message.id,
                '; '.join(sorted(set(limitations))),
            )

        self.db.execute(
            'INSERT OR REPLACE INTO checked VALUES (?,?)',
            (message.id, digest),
        )
        self.db.execute(
            'DELETE FROM pending WHERE id=?',
            (message.id,),
        )
        self.db.commit()

    async def flush_logs(self, log_channel):
        rows = self.db.execute(
            'SELECT id, body FROM outbox'
        ).fetchall()

        for message_id, body in rows:
            await log_channel.send(body)

            self.db.execute(
                'DELETE FROM outbox WHERE id=?',
                (message_id,),
            )
            self.db.commit()

    @tasks.loop(minutes=INTERVAL_MINUTES)
    async def scanner(self):
        try:
            channel = (
                self.get_channel(CHANNEL_ID)
                or await self.fetch_channel(CHANNEL_ID)
            )
            log_channel = (
                self.get_channel(MOD_LOG_ID)
                or await self.fetch_channel(MOD_LOG_ID)
            )

            await self.flush_logs(log_channel)

            row = self.db.execute(
                "SELECT value FROM settings WHERE key='cursor'"
            ).fetchone()

            recent = discord.utils.time_snowflake(
                discord.utils.utcnow() - timedelta(hours=24)
            )

            after = min(int(row[0]), recent) if row else recent
            highest = int(row[0]) if row else after

            async for message in channel.history(
                limit=None,
                after=discord.Object(id=after),
                oldest_first=True,
            ):
                self.db.execute(
                    'INSERT OR IGNORE INTO pending VALUES (?)',
                    (message.id,),
                )
                self.db.commit()

                try:
                    await self.process(channel, message)
                except discord.NotFound:
                    self.db.execute(
                        'DELETE FROM pending WHERE id=?',
                        (message.id,),
                    )
                except Exception as exc:
                    logger.error(
                        'Scan failed for message %s (%s); queued for retry',
                        message.id,
                        type(exc).__name__,
                    )

                highest = max(highest, message.id)

            self.db.execute(
                "INSERT OR REPLACE INTO settings VALUES ('cursor',?)",
                (str(highest),),
            )
            self.db.commit()

            pending = self.db.execute(
                'SELECT id FROM pending WHERE id<=?',
                (after,),
            ).fetchall()

            for (message_id,) in pending:
                try:
                    message = await channel.fetch_message(message_id)
                    await self.process(channel, message)
                except discord.NotFound:
                    self.db.execute(
                        'DELETE FROM pending WHERE id=?',
                        (message_id,),
                    )
                    self.db.commit()
                except Exception as exc:
                    logger.error(
                        'Retry failed for message %s (%s)',
                        message_id,
                        type(exc).__name__,
                    )

            await self.flush_logs(log_channel)

        except Exception as exc:
            logger.error(
                'Scan cycle failed (%s); next attempt in 10 minutes',
                type(exc).__name__,
            )

    @scanner.before_loop
    async def before_scan(self):
        await self.wait_until_ready()
        await asyncio.sleep(INTERVAL_MINUTES * 60)


if __name__ == '__main__':
    Moderator().run(os.environ['DISCORD_TOKEN'])
