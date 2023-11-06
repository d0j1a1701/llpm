from rich_argparse import RichHelpFormatter
from rich.prompt import Confirm
from pathlib import Path
from .style import *
from . import utils
import argparse
import json
import os

root = Path(os.environ.get('LITELOADERQQNT_PROFILE',Path(utils.documentPath()) / 'LiteLoaderQQNT'))
remote_plugins = {}
plugins = {}

def add(args):
	def add_inner(slug:str):
		specify_version = slug.count('@')
		(slug,version) = slug.split('@') if specify_version else (slug,'latest')
		if remote_plugins.get(slug):
			_version = version
			if _version == 'latest':
				_version = remote_plugins[slug]['version']
			if specify_version and not remote_plugins[slug]['repository'].get('use_release'):
				print(f'[error]fetal:[/error] 使用 repo clone 方式下载的插件不支持指定版本')
				return
			if plugins.get(slug) and plugins[slug]['version'] == _version:
				print(f'[error]fetal:[/error] 插件 {plugins[slug]["name"]} 已安装')
				return
			if specify_version:
				utils.add_plugin(root/'plugins',remote_plugins[slug],version)
			else:
				utils.add_plugin(root/'plugins',remote_plugins[slug])
		else:
			print(f'[error]fetal:[/error] 插件 {slug} 不存在')
			print(f'[error]fetal:[/error] 请尝试使用 `llpm update` 更新插件市场缓存')
	for slug in args.slug:
		add_inner(slug)
	
def upgrade(args):
	if args.slug:
		def upgrade_inner(slug):
			if plugins.get(slug):
				if not remote_plugins.get(slug):
					print(f'[error]fetal:[/error] 插件 {slug} 不存在')
					print(f'[error]fetal:[/error] 请尝试使用 `llpm update` 更新插件市场缓存')
					return
				if (not utils.version_less(plugins[slug]['version'] ,remote_plugins[slug]['version'])) and not args.force:
					print(f'llpm: [info]插件 {plugins[slug]["name"]} 已是最新版[/info]')
					return
				print(f'llpm: [cyan]开始更新插件 {plugins[slug]["name"]}[/cyan]')
				utils.remove_plugin(root/'plugins',plugins[slug])
				utils.add_plugin(root/'plugins',remote_plugins[slug])
				print(f'llpm: 插件 [bold][cyan]{remote_plugins[slug]["name"]}[/cyan][/bold] 更新完成 ([bold][cyan]v{plugins[slug]["version"]}[/bold][/cyan] -> [bold][cyan]v{remote_plugins[slug]["version"]}[/bold][/cyan])')
			else:
				print(f'[error]fetal:[/error] 插件 {slug} 未安装')
		for slug in args.slug:
			upgrade_inner(slug)
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
		print(f'llpm: [info]{len(outdated)} 个插件更新完成[/info]')


def update(args):
	if args.index:
		args.index = args.index[0]
		print(f'llpm: [info]读取第三方插件源：{args.index}[/info]')
		with open(root/'llpm.market.json','w',encoding='utf-8') as f:
			json.dump(utils.fetch_plugins(args.index), f,ensure_ascii=False)
	else:
		with open(root/'llpm.market.json','w',encoding='utf-8') as f:
			json.dump(utils.fetch_plugins(), f,ensure_ascii=False)
	print('llpm: [info]插件市场缓存更新完成[/info]')

def remove(args):
	def remove_inner(slug):
		if plugins.get(slug) or args.force:
			name = plugins[slug]["name"] if plugins.get(slug) else slug
			if not plugins.get(slug):
				plugins.update({slug:{'name':slug,'slug':slug,'version':'<unknown>','author':'<unknown>'}})
			if Confirm.ask(f'llpm: [info]卸载插件 {name}?[/info]'):
				try:
					utils.remove_plugin(root/'plugins',plugins[slug])
				except Exception as e:
					print(f'[error]fetal:[/error] 卸载失败：{e} 请结束 QQ 进程后重试')
					print(e.with_traceback)
		else:
			print(f'[error]fetal:[/error] 插件 {slug} 未安装')
			if (root/'plugins'/slug).exists():
				print(f'[warning]warning:[/warning] llpm 的注册插件列表中找不到 {slug}，但是插件目录中存在名为 {slug} 的文件夹')
				print(f'[warning]warning:[/warning] 使用命令 `llpm audit` 尝试自动修复')
				print(f'[warning]warning:[/warning] 使用命令 `llpm remove {slug} --force` 强制卸载该插件')
	for slug in args.slug:
		remove_inner(slug)

def list_plugins(args):
    utils.list_plugins(plugins,'本地插件列表')

def list_market(args):
    utils.list_plugins(remote_plugins,'插件市场')

def audit(args):
	utils.audit(root/'plugins',args.fix)

def run():
	parser = argparse.ArgumentParser(prog='llpm', description='LiteLoaderQQNT 包管理器',formatter_class=RichHelpFormatter)
	subparsers = parser.add_subparsers(title='subcommands', dest='subcommand')

	add_parser = subparsers.add_parser('add', help='安装一个插件')
	add_parser.add_argument('slug', nargs='+', help='需要安装的插件名称')

	upgrade_parser = subparsers.add_parser('upgrade', help='更新一个插件')
	upgrade_parser.add_argument('slug', nargs='*', help='需要更新的插件名称')
	upgrade_parser.add_argument('--force', action='store_true', help='强制更新一个插件')

	update_parser = subparsers.add_parser('update', help='更新本地插件列表缓存')
	update_parser.add_argument('index', nargs='*', help='第三方插件源地址')

	remove_parser = subparsers.add_parser('remove', help='卸载一个插件')
	remove_parser.add_argument('slug', nargs='+', help='需要卸载的插件名称')
	remove_parser.add_argument('--force', action='store_true', help='强制卸载一个插件')

	subparsers.add_parser('list', help='列出当前插件列表')

	subparsers.add_parser('market', help='展示插件市场')

	audit_parser = subparsers.add_parser('audit', help='检查插件目录下可能存在的错误')
	audit_parser.add_argument('--fix', action='store_true', help='修复查找到的错误')

	subparsers.add_parser('data', help='打开 LiteLoader 数据文件夹')

	args = parser.parse_args()

	if not args.subcommand:
		print(r'''[cyan]  _      _      _____  __  __ 
 | |    | |    |  __ \|  \/  |
 | |    | |    | |__) | \  / |
 | |    | |    |  ___/| |\/| |
 | |____| |____| |    | |  | |
 |______|______|_|    |_|  |_|
[/cyan]''')
		print('[cyan]llpm[/cyan]: [cyan]L[/cyan]ite[cyan]L[/cyan]oader [cyan]P[/cyan]ackage [cyan]M[/cyan]anager')
		print('[info]由 [link=https://github.com/d0j1a1701]@d0j1a1701[/link] 开发的适用于 [link=https://llqqnt.mukapp.top]LiteLoaderQQNT[/link] 的开源插件管理器[/info]')
		print('[cyan]代码仓库:[/cyan] [info][link=https://github.com/d0j1a1701/llpm]d0j1a1701/llpm[/link][/info]')
		return 0

	if not (root / 'config.json').exists():
		print('llpm: [error]fetal:[/error] LiteLoader 数据目录未定义')
		print('llpm: [info]请先安装 LiteLoaderQQNT 并使其至少成功启动一次[/info]')
		print('[cyan]代码仓库:[/cyan] [info][link=https://github.com/LiteLoaderQQNT/LiteLoaderQQNT]mo-jinran/LiteLoaderQQNT[/link][/info]')
		print('[cyan]官方网站:[/cyan] [info][link=https://llqqnt.mukapp.top]llqqnt.mukapp.top[/link][/info]')
		print('[cyan]官方群聊:[/cyan] [info][link=https://t.me/LiteLoaderQQNT]Telegram/@LiteLoaderQQNT[/link][/info]')
		return 1

	# 加载远端插件
	global remote_plugins
	if args.subcommand != 'upgrade':
		if (root / 'llpm.market.json').exists():
			try:
				with open(root/'llpm.market.json','r',encoding='utf-8') as f:
					remote_plugins = json.load(f)
			except Exception as e:
				print(f'llpm: [error]error:[/error] 加载插件市场缓存时出现错误: {e}')
				print(f'llpm: [info]忽略缓存重新加载！[/info]')
				update(args)
		else:
			update(args)

	# 加载本地插件
	global plugins
	plugins = utils.load_plugins(root/'plugins')

	if args.subcommand == 'add':
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
	elif args.subcommand == 'data':
		os.startfile(root)