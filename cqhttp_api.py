# CQHTTP API wrapper

from config import *
import aiohttp
import json


async def cqhttp_api(api: str, post_data: dict):
    async with aiohttp.request(
            method="POST", url=f"http://{GO_CQHTTP_HOST}:{GO_CQHTTP_PORT}/{api}",
            data=post_data
    ) as response:
        return await response.json()


async def send_group_msg(group_id, message: str):
    return await cqhttp_api(
        'send_msg',
        {'message_type': 'group', 'group_id': group_id, 'message': message}
    )


async def send_private_msg(user_id, message: str):
    return await cqhttp_api(
        'send_msg',
        {'message_type': 'private', 'user_id': user_id, 'message': message}
    )


async def send_group_forward_msg(group_id, messages: list[str], sender_name: str):
    nodes = []
    for message in messages:
        nodes.append(
            {
                'type': 'node',
                'data': {
                    'name': sender_name,
                    'uin': GO_CQHTTP_USER_ID,
                    'content': [
                        {
                            'type': 'text',
                            'data': {'text': message}
                        }
                    ]
                }
            }
        )
    return await cqhttp_api(
        'send_group_forward_msg',
        {'message_type': 'group', 'group_id': group_id, 'messages': json.dumps(nodes)}
    )


async def delete_msg(message_id):
    return await cqhttp_api(
        'delete_msg',
        {'message_id': message_id}
    )
