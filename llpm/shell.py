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
	print(f'llpm: [info]初始化 LiteLoader 数据目录:{root}[/info]')
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
			if not utils.version_less(plugins[args.slug]['version'] ,remote_plugins[args.slug]['version']):
				print(f'llpm: [info]插件 {plugins[args.slug]["name"]} 已是最新版[/info]')
				return
			print(f'[info]开始更新插件 {plugins[args.slug]["name"]}[/info]')
			utils.remove_plugin(root/'plugins',plugins[args.slug])
			utils.add_plugin(root/'plugins',remote_plugins[args.slug])
		else:
			print(f'[error]fetal:[/error] 插件 {args.slug} 未安装')
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
	print(f'llpm: [warning]警告：{len(outdated)} 个插件不是最新版[/warning]')
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
	if plugins.get(args.slug):
		if Confirm.ask(f'[info]卸载插件 {plugins[args.slug]["name"]}?[/info]'):
			try:
				utils.remove_plugin(root/'plugins',plugins[args.slug])
			except PermissionError as e:
				print(f'[error]fetal:[/error] 卸载失败：权限不足')
				print(f'[error]fetal:[/error] 请尝试用带管理员权限/ root 账户的终端卸载')
	else:
		print(f'[error]fetal:[/error] 插件 {args.slug} 未安装')
	

def list_plugins(args):
    utils.list_plugins(plugins,'本地插件列表')

def list_market(args):
    utils.list_plugins(remote_plugins,'插件市场')

def run():
	parser = argparse.ArgumentParser(prog='llpm', description='LiteLoaderQQNT 包管理器')
	subparsers = parser.add_subparsers(title='subcommands', dest='subcommand', required=True)

	# 创建 init 子命令的解析器
	subparsers.add_parser('init', help='将当前目录初始化为 LiteLoader 数据目录')

	# 创建 add 子命令的解析器
	add_parser = subparsers.add_parser('add', help='安装一个插件')
	add_parser.add_argument('slug', help='需要安装的插件名称')

	# 创建 upgrade 子命令的解析器
	upgrade_parser = subparsers.add_parser('upgrade', help='更新一个插件')
	upgrade_parser.add_argument('slug', nargs='?', help='需要更新的插件名称')

	# 创建 update 子命令的解析器
	subparsers.add_parser('update', help='更新本地插件列表缓存')

	# 创建 remove 子命令的解析器
	remove_parser = subparsers.add_parser('remove', help='卸载一个插件')
	remove_parser.add_argument('slug', help='需要卸载的插件名称')

	# 创建 list 子命令的解析器
	subparsers.add_parser('list', help='列出当前插件列表')
 
	# 创建 market 子命令的解析器
	subparsers.add_parser('market', help='展示插件市场')

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