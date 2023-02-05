#!/usr/bin/env python3

from fastapi import (
    FastAPI,
    Request
)
import uvicorn
import asyncio
import os
import json

from config import *
import api
import cqhttp_api
from models import *
import activities


def start_gocq():
    import subprocess
    go_cqhttp_path = os.getenv(
        'GO_CQHTTP_PATH',
        os.getcwd() + '/go-cqhttp'
    )
    subprocess.Popen(
        [go_cqhttp_path, '-c', 'config_gocq.yml']
    )


app = FastAPI()


@app.on_event("startup")
async def startup_event():
    if not GO_CQHTTP_STANDALONE:
        start_gocq()


@app.post('/')
async def cqhttp_event(
        data: CQHTTPRequest
) -> CQHTTPQuickReply | dict:
    def get_cmdline(message: str) -> str | None:
        for line in message.splitlines(keepends=False):
            line = line.strip()
            if line.startswith("e!"):
                return line
        return None

    match data.post_type:
        case CQHTTPEventType.message:
            if data.group_id not in BOT_ENABLED_GROUPS:
                return {'status': 'failed'}
            commands = {
                'e!help': activities.command_help,
                'e!register': activities.command_register,
                'e!permission': activities.command_permission,
                'e!ban': activities.command_ban,
                'e!unban': activities.command_unban,
                'e!query': activities.command_query,
                'e!random': activities.command_random,
                'e!stats': activities.command_stats,
                'e!server': activities.command_server
            }
            cmdline = get_cmdline(data.message)
            for command in commands:
                if cmdline.startswith(command):
                    arg_string = cmdline.replace(command, '').strip()
                    command_return = await commands[command](
                        data=data,
                        arg_string=arg_string
                    )
                    if isinstance(command_return, CQHTTPQuickReply):
                        return command_return
                    else:
                        return {'status': 'ok'}
            if cmdline is not None:
                return activities.reply(
                    message='❌ 命令用法不正确，请输入 e!help 查看帮助。'
                )
        case CQHTTPEventType.notice:
            match data.notice_type:
                case CQHTTPNoticeType.group_decrease:
                    response_json = await api.update_permission(
                        user_identifier=str(data.sender.user_id),
                        permission='valid',
                        value=False
                    )
                    if 'success' in response_json:
                        await cqhttp_api.send_group_msg(
                            data.group_id,
                            f'👤 {response_json["username"]} ({data.sender.user_id}) 已经退群，'
                            f'所以帐号暂时冻结。下次入群时将恢复可玩。'
                        )
                    else:

                        await cqhttp_api.send_group_msg(
                            data.group_id,
                            f'👤 {response_json["username"]} ({data.sender.user_id}) 已经退群，'
                            f'但并没有注册引擎部落账号。所以不进行操作。'
                        )
                case CQHTTPNoticeType.group_increase:
                    await api.update_permission(
                        user_identifier=str(data.sender.user_id),
                        permission='valid',
                        value=True
                    )
            return {'status': 'ok'}


@app.post('/github')
async def github_payload(request: Request):
    webhook = await request.json()
    if 'head_commit' in webhook:  # push
        message = (
            f'📤 {webhook["repository"]["name"]} 代码库中有了新提交:\n'
            f'{webhook["head_commit"]["message"]}\n'
            f'By {webhook["head_commit"]["committer"]["name"]}'
        )
        for group in BOT_ENABLED_GROUPS:
            await cqhttp_api.send_group_msg(group_id=group, message=message)
        return 'Success'
    elif 'workflow_run' in webhook:
        if webhook["action"] == 'completed':
            message = f'📤 {webhook["repository"]["name"]} 代码库中的网页部署完成:\n' \
                      f'{webhook["workflow_run"]["head_commit"]["message"]}'
            for group in BOT_ENABLED_GROUPS:
                await cqhttp_api.send_group_msg(group_id=group, message=message)
                return 'Success'
    elif 'release' in webhook:
        if webhook["action"] == 'published':
            message = f'⏩ [CQ:at,qq=all] 引擎部落服务器发布了新的大版本: {webhook["release"]["tag_name"]} !\n' \
                      f'更新日志如下:\n' \
                      f'{webhook["release"]["body"]}'
            for group in BOT_ENABLED_GROUPS:
                await cqhttp_api.send_group_msg(group_id=group, message=message)
                return 'Success'
    for group in BOT_ENABLED_GROUPS:
        await cqhttp_api.send_group_msg(
            group_id=group,
            message=f'❌ 接收到了新的 GitHub 推送消息，但并未实现对应的推送条目。\n'
                    f'{json.dumps(webhook, ensure_ascii=False)}'
        )
    return 'NotImplemented'


@app.post('/enginetribe')
async def enginetribe_payload(request: Request):
    webhook: dict = await request.json()
    message: str = ''
    match webhook["type"]:
        case 'new_arrival':  # new arrival
            message = f'📤 {webhook["author"]} 上传了新关卡: {webhook["level_name"]}\n' \
                      f'ID: {webhook["level_id"]}'
        case 'new_featured':  # new featured
            message = f'🌟 {webhook["author"]} 的关卡 {webhook["level_name"]} 被加入了管理推荐关卡，快来玩!\n' \
                      f'ID: {webhook["level_id"]}'
        case 'permission_change':
            permission_name = {'booster': '捐赠者', 'mod': '关卡管理员'}[webhook['permission']]
            message = f"{'🤗' if webhook['value'] else '😥'} " \
                      f"{webhook['username']} {'获得' if webhook['value'] else '失去'}了" \
                      f"引擎部落的{permission_name}权限！"
        case _:
            if 'likes' in webhook["type"]:  # 10/100/1000 likes
                message = f'🎉 恭喜，{webhook["author"]} 的关卡 {webhook["level_name"]} 获得了 ' \
                          f'{webhook["type"].replace("_likes", "")} 个点赞!\n' \
                          f'ID: {webhook["level_id"]}'
            if 'plays' in webhook["type"]:  # 100/1000 plays
                message = f'🎉 恭喜，{webhook["author"]} 的关卡 {webhook["level_name"]} 已经被游玩了 ' \
                          f'{webhook["type"].replace("_plays", "")} 次!\n' \
                          f'ID: {webhook["level_id"]}'
            if 'deaths' in webhook["type"]:  # 100/1000 deaths
                message = f'🔪 {webhook["author"]} 的关卡 {webhook["level_name"]} 已经夺得了 ' \
                          f'{webhook["type"].replace("_deaths", "")} 个人头，快去挑战吧!\n' \
                          f'ID: {webhook["level_id"]}'
            if 'clears' in webhook["type"]:  # 100/1000 clears
                message = f'🎉 恭喜，{webhook["author"]} 的关卡 {webhook["level_name"]} 已经被通关 ' \
                          f'{webhook["type"].replace("_clears", "")} 次，快去挑战吧!\n' \
                          f'ID: {webhook["level_id"]}'
    if message != '':
        for group in BOT_ENABLED_GROUPS:
            await cqhttp_api.send_group_msg(group_id=group, message=message)
        return 'Success'
    else:
        for group in BOT_ENABLED_GROUPS:
            await cqhttp_api.send_group_msg(
                group_id=group,
                message=f'❌ 接收到了新的引擎部落推送消息，但并未实现对应的推送条目。\n'
                        f'{json.dumps(webhook, ensure_ascii=False)}'
            )
        return 'NotImplemented'


def run():
    loop = asyncio.new_event_loop()
    webhook_server = uvicorn.Server(
        config=uvicorn.Config(
            app,
            host=WEBHOOK_HOST,
            port=WEBHOOK_PORT,
            loop="asyncio",
            workers=1
        )
    )
    loop.run_until_complete(webhook_server.serve())


if __name__ == '__main__':
    run()
