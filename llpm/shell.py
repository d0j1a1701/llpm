from rich_argparse import RichHelpFormatter
from rich.prompt import Confirm
from pathlib import Path
from .style import *
from . import utils
import argparse
import json

root = Path.cwd()
remote_plugins = {}
plugins = {}

def init(args):
	print(f'llpm: [info]初始化 LiteLoader 数据目录: [cyan]{root}[/cyan][/info]')
	(root / 'llpm.config.json').touch()

def add(args):
	if remote_plugins.get(args.slug):
		utils.add_plugin(root/'plugins',remote_plugins[args.slug])
	else:
		print(f'[error]fetal:[/error] 插件 {args.slug} 不存在')
		print(f'[error]fetal:[/error] 请尝试使用 `llpm update` 更新插件列表缓存')
  
	
def upgrade(args):
	if args.slug:
		if plugins.get(args.slug):
			if not remote_plugins.get(args.slug):
				print(f'[error]fetal:[/error] 插件 {args.slug} 不存在')
				print(f'[error]fetal:[/error] 请尝试使用 `llpm update` 更新插件列表缓存')
				return
			if (not utils.version_less(plugins[args.slug]['version'] ,remote_plugins[args.slug]['version'])) and not args.force:
				print(f'llpm: [info]插件 {plugins[args.slug]["name"]} 已是最新版[/info]')
				return
			print(f'llpm: [cyan]开始更新插件 {plugins[args.slug]["name"]}[/cyan]')
			utils.remove_plugin(root/'plugins',plugins[args.slug])
			utils.add_plugin(root/'plugins',remote_plugins[args.slug])
			print(f'llpm: 插件 [bold][cyan]{remote_plugins[args.slug]["name"]}[/cyan][/bold] 更新完成 ([bold][cyan]v{plugins[args.slug]["version"]}[/bold][/cyan] -> [bold][cyan]v{remote_plugins[args.slug]["version"]}[/bold][/cyan])')
		else:
			print(f'[error]fetal:[/error] 插件 {args.slug} 未安装')
		return
	if args.force:
		print(f'[error]fetal:[/error] 不能强制更新全部插件')
		return
	outdated = []
	for slug in plugins:
		remote = remote_plugins.get(slug)
		plugin = plugins.get(slug)
		if not remote or not plugin:
			continue
		if remote and utils.version_less(plugin['version'],remote['version']):
			outdated.append(plugin)
	if not len(outdated):
		print('llpm: [info]所有插件均已是最新版！[/info]')
		return
	print(f'llpm: [warning]warning:[/warning] {len(outdated)} 个插件不是最新版')
	for plugin in outdated:
		print(f'  - {plugin["name"]} [bold][cyan]v{plugin["version"]}[/cyan][/bold] → [bold][cyan]v{remote_plugins[plugin["slug"]]["version"]}[/cyan][/bold]')
	if Confirm.ask('[info]是否更新以上插件？[/info]'):
		for plugin in outdated:
			print(f'[info]开始更新插件 {plugin["name"]}[/info]')
			utils.remove_plugin(root/'plugins',plugin)
			utils.add_plugin(root/'plugins',remote_plugins[plugin["slug"]])


def update(args):
	with open(root/'llpm.market.json','w',encoding='utf-8') as f:
		json.dump(utils.fetch_plugins(), f,ensure_ascii=False)
	print('llpm: [info]插件列表缓存更新完成[/info]')

def remove(args):
	if plugins.get(args.slug) or args.force:
		name = plugins[args.slug]["name"] if plugins.get(args.slug) else args.slug
		if not plugins.get(args.slug):
			plugins.update({args.slug:{'name':args.slug,'slug':args.slug,'version':'<unknown>','author':'<unknown>'}})
		if Confirm.ask(f'llpm: [info]卸载插件 {name}?[/info]'):
			try:
				utils.remove_plugin(root/'plugins',plugins[args.slug])
			except PermissionError as e:
				print(f'[error]fetal:[/error] 卸载失败：权限不足')
				print(f'[error]fetal:[/error] 请尝试用带管理员权限/ root 账户的终端卸载')
				print(f'[error]fetal:[/error] 或结束 QQ 进程后重试')
	else:
		print(f'[error]fetal:[/error] 插件 {args.slug} 未安装')
		if (root/'plugins'/args.slug).exists():
			print(f'[warning]warning:[/warning] llpm 的注册插件列表中找不到 {args.slug}，但是插件目录中存在名为 {args.slug} 的文件夹')
			print(f'[warning]warning:[/warning] 这可能是因为该插件的目录结构不规范，llpm 无法解析，你可以尝试自动修复、手动处理或强制卸载该插件')
			print(f'[warning]warning:[/warning] 使用命令 `llpm audit` 尝试自动修复')
			print(f'[warning]warning:[/warning] 使用命令 `llpm remove {args.slug} --force` 强制卸载该插件')
	

def list_plugins(args):
    utils.list_plugins(plugins,'本地插件列表')

def list_market(args):
    utils.list_plugins(remote_plugins,'插件市场')

def audit(args):
	utils.audit(root/'plugins',args.fix)

def run():
	parser = argparse.ArgumentParser(prog='llpm', description='LiteLoaderQQNT 包管理器',formatter_class=RichHelpFormatter)
	subparsers = parser.add_subparsers(title='subcommands', dest='subcommand', required=True)

	# 创建 init 子命令的解析器
	subparsers.add_parser('init', help='将当前目录初始化为 LiteLoader 数据目录')

	# 创建 add 子命令的解析器
	add_parser = subparsers.add_parser('add', help='安装一个插件')
	add_parser.add_argument('slug', help='需要安装的插件名称')

	# 创建 upgrade 子命令的解析器
	upgrade_parser = subparsers.add_parser('upgrade', help='更新一个插件')
	upgrade_parser.add_argument('slug', nargs='?', help='需要更新的插件名称')
	upgrade_parser.add_argument('--force', action='store_true', help='强制更新一个插件')

	# 创建 update 子命令的解析器
	subparsers.add_parser('update', help='更新本地插件列表缓存')

	# 创建 remove 子命令的解析器
	remove_parser = subparsers.add_parser('remove', help='卸载一个插件')
	remove_parser.add_argument('slug', help='需要卸载的插件名称')
	remove_parser.add_argument('--force', action='store_true', help='强制卸载一个插件')

	# 创建 list 子命令的解析器
	subparsers.add_parser('list', help='列出当前插件列表')
 
	# 创建 market 子命令的解析器
	subparsers.add_parser('market', help='展示插件市场')

	# 创建 audit 子命令的解析器
	audit_parser = subparsers.add_parser('audit', help='检查插件目录下可能存在的错误')
	audit_parser.add_argument('--fix', action='store_true', help='修复查找到的错误')

	args = parser.parse_args()

	if args.subcommand != 'init' and not (root / 'llpm.config.json').exists():
		print('[error]fetal:[/error] LiteLoader 数据目录未定义')
		print('[error]fetal:[/error] 请在 LiteLoader 数据目录下运行 `llpm init` 以确定数据目录')
		return 1

	# 加载远端插件
	global remote_plugins
	if (root / 'llpm.market.json').exists():
		with open(root/'llpm.market.json','r',encoding='utf-8') as f:
			remote_plugins = json.load(f)
	else:
		update(args)

	# 加载本地插件
	global plugins
	plugins = utils.load_plugins(root/'plugins')

	if args.subcommand == 'init':
		init(args)
	elif args.subcommand == 'add':
		add(args)
	elif args.subcommand == 'upgrade':
		upgrade(args)
	elif args.subcommand == 'update':
		update(args)
	elif args.subcommand == 'remove':
		remove(args)
	elif args.subcommand == 'list':
		list_plugins(args)
	elif args.subcommand == 'market':
		list_market(args)
	elif args.subcommand == 'audit':
		audit(args)