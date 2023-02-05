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


def mention(data: CQHTTPRequest) -> str:
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
        ('e!help', '❔️ 查看此帮助'),
        ('e!register <注册码>', '📝 注册帐号或修改密码'),
        ('e!query <ID>', '🔍 查询关卡信息'),
        ('e!stats <用户名|QQ号>', '📊 查看上传记录'),
        ('e!random [难度]', '🎲 来个随机关卡'),
        ('e!server', '🗄️ 查看服务器状态')
    ]

    admin_command_helps: list[tuple] = [
        ('e!permission <用户名|QQ号>', '👤 修改用户权限'),
    ]
    stage_mod_command_helps: list[tuple] = [
        ('e!ban <用户名|QQ号>', '⛔ 封禁用户'),
        ('e!unban <用户名|QQ号>', '✅ 解封用户')
    ]

    def help_item(command_name: str, command_description: str):
        return f'{command_name}: {command_description}。\n'

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
) -> CQHTTPQuickReply | None:
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
                            message=f'🎉 {mention(data)} 注册成功，'
                                    f'现在可以使用 {response_json["username"]} 在游戏中登录了。',
                            delete=True
                        )
                    else:
                        if response_json['error_type'] == '035':
                            return reply(
                                message=f'❌ 注册失败，一个 QQ 号只能注册一个帐号。\n'
                                        f'{mention(data)} ({response_json["username"]}) 不能再注册账号了。',
                                delete=True
                            )
                        elif response_json['error_type'] == '036':
                            return reply(
                                message=f'❌ {mention(data)} 注册失败。\n'
                                        f'{response_json["username"]} 用户名已经存在，请回到注册网页换一个用户名。',
                                delete=True
                            )
                        else:
                            return reply(
                                message=f'❌ {mention(data)} 注册失败，发生未知错误。\n'
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
                            message=f'🎉 {mention(data)} ({response_json["username"]}) 的密码修改成功。',
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


async def command_permission(
        data: CQHTTPRequest,
        arg_string: str
) -> CQHTTPQuickReply | None:
    if data.sender.role != CQHTTPMessageSenderRole.owner:
        return reply(
            message=f'❌ {mention(data)} 无权使用该命令。'
        )
    if not arg_string:
        return reply(
            '使用方法: e!permission <用户名|用户QQ号> <权限名> <true|false>\n'
            '权限列表: mod, admin, booster, valid, banned'
        )
    else:
        try:
            permission_args = arg_string.split(' ')
            user_identifier: str = permission_args[0]
            permission_name: str = permission_args[1]
            permission_value: str = permission_args[2]
            if permission_value not in ['true', 'false']:
                return reply(
                    message=f'❌ {mention(data)} 权限值必须为 true 或 false。'
                )
            permission_value: bool = (permission_value == 'true')
            if permission_name not in ['mod', 'admin', 'booster', 'valid', 'banned']:
                return reply(
                    message=f'❌ {mention(data)} 无效的权限名。'
                )
            response_json = await api.update_permission(
                user_identifier=user_identifier,
                permission=permission_name,
                value=permission_value
            )
            if 'success' in response_json:
                return reply(
                    message=f'✅ {response_json["username"]} 的权限修改成功。',
                )
            else:
                return reply(
                    message=f'❌ {mention(data)} 修改权限失败。\n'
                            f'{response_json["error_type"]} - {response_json["message"]}'
                )
        except Exception as e:
            return reply(
                message=f'❌ {mention(data)} 修改权限失败，发生未知错误。\n'
                        f'{str(e)}'
            )


async def command_ban(
        data: CQHTTPRequest,
        arg_string: str
) -> CQHTTPQuickReply | None:
    if data.sender.role not in [CQHTTPMessageSenderRole.admin, CQHTTPMessageSenderRole.owner]:
        return reply(
            message=f'❌ {mention(data)} 无权使用该命令。'
        )
    if not arg_string:
        return reply(
            '使用方法: e!ban <用户名|QQ号>',
        )
    else:
        try:
            response_json = await api.update_permission(
                user_identifier=arg_string.strip(),
                permission='banned',
                value=True
            )
            if 'success' in response_json:
                return reply(
                    message=f'✅ {mention(data)} ({response_json["username"]}) 封禁成功。',
                )
            else:
                return reply(
                    message=f'❌ {mention(data)} 修改权限失败。\n'
                            f'{response_json["error_type"]} - {response_json["message"]}'
                )
        except Exception as e:
            return reply(
                message=f'❌ {mention(data)} 修改权限失败，发生未知错误。\n'
                        f'{str(e)}'
            )


async def command_unban(
        data: CQHTTPRequest,
        arg_string: str
) -> CQHTTPQuickReply | None:
    if data.sender.role not in [CQHTTPMessageSenderRole.admin, CQHTTPMessageSenderRole.owner]:
        return reply(
            message=f'❌ {mention(data)} 无权使用该命令。'
        )
    if not arg_string:
        return reply(
            '使用方法: e!unban <用户名|QQ号>',
        )
    else:
        try:
            response_json = await api.update_permission(
                user_identifier=arg_string.strip(),
                permission='banned',
                value=False
            )
            if 'success' in response_json:
                return reply(
                    message=f'✅ {mention(data)} ({response_json["username"]}) 解封成功。',
                )
            else:
                return reply(
                    message=f'❌ {mention(data)} 修改权限失败。\n'
                            f'{response_json["error_type"]} - {response_json["message"]}'
                )
        except Exception as e:
            return reply(
                message=f'❌ {mention(data)} 修改权限失败，发生未知错误。\n'
                        f'{str(e)}'
            )


async def command_query(
        data: CQHTTPRequest,
        arg_string: str
) -> CQHTTPQuickReply | None:
    if not arg_string:
        return reply(
            '使用方法: e!query <关卡 ID>',
        )
    else:
        if '-' in arg_string:
            level_id = arg_string.strip().upper()
        else:
            level_id = prettify_level_id(arg_string.strip())
        try:
            auth_code = await api.login_session(
                token=API_TOKEN
            )
            response_json = await api.query_level(
                level_id=level_id,
                auth_code=auth_code
            )
            if 'error_type' in response_json:
                return reply(
                    f'❌ 关卡 {level_id} 未找到。'
                )
            else:
                level_data: dict = response_json['result']
                return reply(
                    level_query_metadata(level_data, '🔍 查询结果')
                )
        except Exception as e:
            return reply(
                message=f'❌ 查询失败，发生未知错误。\n'
                        f'{str(e)}'
            )


async def command_random(
        data: CQHTTPRequest,
        arg_string: str
) -> CQHTTPQuickReply | None:
    if arg_string:
        difficulty_ids: dict[str, int] = {
            # SMM1 风格的难度名
            '简单': 0, '普通': 1, '专家': 2, '超级专家': 3,
            # SMM2 风格的难度名
            '困难': 2, '极难': 3,
            # TGRCode API 风格的难度 ID
            'e': 0, 'n': 1, 'ex': 2, 'sex': 3,
            # SMMWE API 风格的难度 ID
            '0': 0, '1': 1, '2': 2, '3': 3
        }
        difficulty_str_id = arg_string.strip().lower()
        if difficulty_str_id not in difficulty_ids:
            return reply(
                '❌ 无效的难度。\n'
                '可用的难度名或 ID: 简单、普通、专家、超级专家、困难、极难、e、n、ex、sex。'
            )
        else:
            difficulty_id: str = str(difficulty_ids[difficulty_str_id])
    else:
        difficulty_id: None = None
    try:
        auth_code = await api.login_session(
            token=API_TOKEN
        )
        response_json = await api.random_level(
            auth_code=auth_code,
            difficulty=difficulty_id
        )
        level_data: dict = response_json['result']
        return reply(
            level_query_metadata(level_data, '🎲 随机关卡')
        )
    except Exception as e:
        return reply(
            message=f'❌ 查询失败，发生未知错误。\n'
                    f'{str(e)}'
        )


async def command_server(
        data: CQHTTPRequest,
        arg_string: str
) -> CQHTTPQuickReply | None:
    server_stats = await api.server_stats()
    return reply(
        f'🗄️ 服务器状态\n'
        f'🐧 操作系统: {server_stats.os}\n'
        f'🐍 Python 版本: {server_stats.python}\n'
        f'👥 玩家数量: {server_stats.player_count}\n'
        f'🌏 关卡数量: {server_stats.level_count}\n'
        f'🕰️ 运行时间: {int(server_stats.uptime / 60)} 分钟\n'
        f'📊 每分钟连接数: {server_stats.connection_per_minute}'
    )


async def command_stats(
        data: CQHTTPRequest,
        arg_string: str
) -> CQHTTPQuickReply | None:
    if arg_string:
        user_identifier = arg_string.strip()
    else:
        user_identifier = str(data.sender.user_id)
    try:
        user_info_response_json = await api.user_info(
            user_identifier=user_identifier
        )
        if 'error_type' in user_info_response_json:
            return reply(
                f'❌ 用户 {user_identifier} 未找到。'
            )
        else:
            user_data = user_info_response_json['result']
            messages: list[str] = [
                f'📜 玩家 {user_data["username"]} 的上传记录\n'
                f'共上传了 {user_data["uploads"]} 个关卡。'
            ]
            if int(user_data['uploads']) == 0:
                # 没有关卡
                return reply(
                    messages[0]
                )
            else:
                auth_code = await api.login_session(
                    token=API_TOKEN
                )
                all_likes: int = 0
                all_dislikes: int = 0
                levels: list[dict] = await api.get_user_levels(
                    auth_code=auth_code,
                    username=user_data['username']
                )
                for level_data in levels:
                    messages.append(
                        f'- {level_data["name"]}'
                        f"{' (✨)' if (int(level_data['featured']) == 1) else ''}\n"
                        f'  ❤ {level_data["likes"]} | 💙 {level_data["dislikes"]}\n'
                        f'  ID: {level_data["id"]}'
                        f'  🏷️ {level_data["etiquetas"]}'
                    )
                    all_likes += int(level_data['likes'])
                    all_dislikes += int(level_data['dislikes'])
                messages.append(
                    f'❤ 总获赞: {all_likes} | '
                    f'💙 总获孬: {all_dislikes}'
                )
                await cqhttp_api.send_group_forward_msg(
                    group_id=data.group_id,
                    messages=messages,
                    sender_name=f'{user_data["username"]} 的上传记录'
                )
                return None
    except Exception as e:
        return reply(
            message=f'❌ 查询失败，发生未知错误。\n'
                    f'{str(e)}'
        )
