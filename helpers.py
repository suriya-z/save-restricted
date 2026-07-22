import re
import os
import asyncio
import subprocess

def is_owner(user_id: int) -> bool:
    return user_id in config.OWNER_IDS

async def schedule_auto_delete(client, chat_id: int, message_ids, delay_seconds: int = 300):
    async def _delete():
        await asyncio.sleep(delay_seconds)
        try:
            if isinstance(message_ids, list):
                await client.delete_messages(chat_id, message_ids)
            else:
                await client.delete_messages(chat_id, message_ids)
        except Exception as e:
            print(f'Auto-delete error: {e}')
    asyncio.create_task(_delete())

def get_video_metadata(video_path: str):
    duration = 0
    width = 0
    height = 0
    thumb_path = None
    try:
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration:stream=width,height',
            '-of', 'default=noprint_wrappers=1', video_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        for line in res.stdout.splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                k, v = k.strip(), v.strip()
                if k == 'duration':
                    try: duration = int(float(v))
                    except: pass
                elif k == 'width':
                    try: width = int(v)
                    except: pass
                elif k == 'height':
                    try: height = int(v)
                    except: pass
    except Exception as e:
        print(f'ffprobe notice: {e}')

    try:
        t_path = video_path + '_thumb.jpg'
        cmd_thumb = [
            'ffmpeg', '-y', '-ss', '00:00:01',
            '-i', video_path, '-vframes', '1',
            '-q:v', '2', t_path
        ]
        subprocess.run(cmd_thumb, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        if os.path.exists(t_path) and os.path.getsize(t_path) > 0:
            thumb_path = t_path
    except Exception as e:
        print(f'ffmpeg notice: {e}')

    return duration, width, height, thumb_path

def parse_duration(duration_str: str) -> int:
    if not duration_str:
        return 0
    match = re.match(r'^(\d+)\s*(m|min|minutes|h|hr|hours|d|day|days)$', duration_str.lower().strip())
    if not match:
        return 0
    val = int(match.group(1))
    unit = match.group(2)
    if unit in ['m', 'min', 'minutes']:
        return val * 60
    elif unit in ['h', 'hr', 'hours']:
        return val * 3600
    elif unit in ['d', 'day', 'days']:
        return val * 86400
    return 0
