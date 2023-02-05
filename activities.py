import api

from models import *
from config import *
import cqhttp_api

import base64
import hashlib
from binascii import Error as BinAsciiError


def reply(
        message: str,
        at_sender: bool = False,
        delete: bool = False
) -> CQHTTPQuickReply:
    return CQHTTPQuickReply(
        reply=message,
        at_sender=at_sender,
        delete=delete,
        auto_escape=False if ('[CQ:' in message) else True
    )


def at(data: CQHTTPRequest) -> str:
    return f'[CQ:at,qq={data.sender.user_id}]'


def prettify_level_id(level_id: str):
    return level_id[0:4] + '-' + level_id[4:8] + '-' + level_id[8:12] + '-' + level_id[12:16]


def level_query_metadata(level_data: dict, metadata_type: str) -> str:
    styles: list[str] = ['超马1', '超马3', '超马世界', '新超马U']

    def clear_rate(deaths, clears, plays) -> str:
        if int(deaths) == 0:
            return f'{str(clears)}次通关 / {str(plays)}次游玩'
        else:
            return f'{str(clears)}次通关 / {str(plays)}次游玩 {round((int(clears) / int(plays)) * 100, 2)} %'

    message: str = (f'{metadata_type}: {level_data["id"]} {level_data["name"]} \n'
                    f'作者: {level_data["author"]}\n'
                    f'上传于 {level_data["date"]}\n'
                    f'{level_data["likes"]}❤  {level_data["dislikes"]}💙')
    message += ' (管理推荐关卡)\n' if (int(level_data['featured']) == 1) else '\n'
    message += f"{clear_rate(level_data['muertes'], level_data['victorias'], level_data['intentos'])}\n"
    message += f'标签: {level_data["etiquetas"]}, 游戏风格: {styles[int(level_data["apariencia"])]}'
    return message


async def command_help(
        data: CQHTTPRequest,
        arg_string: str
) -> None:
    command_helps: list[tuple] = [
        ('help', '查看此帮助'),
        ('register', '注册帐号或修改密码'),
        ('query', '查询关卡信息'),
        ('report', '向管理组举报关卡'),
        ('stats', '查看上传记录'),
        ('random', '来个随机关卡'),
        ('server', '查看服务器状态')
    ]

    admin_command_helps: list[tuple] = [
        ('permission', '修改用户权限'),
        ('execute', '执行命令')
    ]
    stage_mod_command_helps: list[tuple] = [
        ('ban', '封禁用户'),
        ('unban', '解封用户')
    ]

    def help_item(command_name: str, command_description: str):
        return f'e!{command_name}: {command_description}。\n'

    messages: list[str] = []
    message = f'📑 可用的命令 (输入命令以查看用法):\n'
    for command, description in command_helps:
        message += help_item(command, description)
    messages.append(message)
    if data.sender.user_id in BOT_ADMIN:
        message = '📑 可用的管理命令:\n'
        for command, description in admin_command_helps:
            message += help_item(command, description)
        messages.append(message)
    if data.sender.role in [CQHTTPMessageSenderRole.admin, CQHTTPMessageSenderRole.owner]:
        message = '📑 可用的游戏管理命令:\n'
        for command, description in stage_mod_command_helps:
            message += help_item(command, description)
        messages.append(message)
    await cqhttp_api.send_group_forward_msg(
        group_id=data.group_id,
        messages=messages,
        sender_name='帮助'
    )
    return


async def command_register(
        data: CQHTTPRequest,
        arg_string: str
):
    def parse_register_code(raw_register_code_input: str) -> RegisterCode:
        try:  # auto add equal sign
            register_code_list = base64.b64decode(
                raw_register_code_input.encode()
            ).decode().split("\n")
        except BinAsciiError:
            try:
                register_code_list = base64.b64decode(
                    (raw_register_code_input + '=').encode()
                ).decode().split("\n")
            except BinAsciiError:
                register_code_list = base64.b64decode(
                    (raw_register_code_input + '==').encode()
                ).decode().split("\n")
        return RegisterCode(
            operation=RegisterCodeOperation(register_code_list[0]),
            username=register_code_list[1],
            password_hash=register_code_list[2],
        )

    if not arg_string:
        return reply(
            '🔗 打开 https://web.enginetribe.gq/user/register 以注册。\n'
            '打开 https://web.enginetribe.gq/user/change_password 以修改密码。'
        )
    else:
        try:
            raw_register_code: str = arg_string.split(' ')[0]
            register_code: RegisterCode = parse_register_code(raw_register_code)
            match register_code.operation:
                case RegisterCodeOperation.register:
                    response_json = await api.user_register(
                        username=register_code.username,
                        password_hash=register_code.password_hash,
                        im_id=data.sender.user_id
                    )
                    if 'success' in response_json:
                        return reply(
                            message=f'🎉 {at(data)} 注册成功，'
                                    f'现在可以使用 {response_json["username"]} 在游戏中登录了。',
                            delete=True
                        )
                    else:
                        if response_json['error_type'] == '035':
                            return reply(
                                message=f'❌ 注册失败，一个 QQ 号只能注册一个帐号。\n'
                                        f'{at(data)} ({response_json["username"]}) 不能再注册账号了。',
                                delete=True
                            )
                        elif response_json['error_type'] == '036':
                            return reply(
                                message=f'❌ {at(data)} 注册失败。\n'
                                        f'{response_json["username"]} 用户名已经存在，请回到注册网页换一个用户名。',
                                delete=True
                            )
                        else:
                            return reply(
                                message=f'❌ {at(data)} 注册失败，发生未知错误。\n'
                                        f'{response_json["error_type"]} - {response_json["message"]}',
                                delete=True
                            )
                case RegisterCodeOperation.change_password:
                    response_json = await api.update_password(
                        user_identifier=register_code.username,
                        password_hash=register_code.password_hash,
                        im_id=data.sender.user_id
                    )
                    if 'success' in response_json:
                        return reply(
                            message=f'🎉 {at(data)} ({response_json["username"]}) 的密码修改成功。',
                            delete=True
                        )
                    else:
                        return reply(
                            message='❌ 修改密码失败，非本人操作。',
                            delete=True
                        )
        except Exception as e:
            str_exception: str = str(e)
            if 'BinAsciiError' in str_exception:
                return reply(
                    message=f'❌ 无效的注册码，请检查是否复制完全。',
                    delete=True
                )
            else:
                return reply(
                    message=f'❌ 无效的注册码，注册码格式出现错误。\n'
                            f'错误信息: {str_exception}',
                    delete=True
                )
