from rich.progress import Progress,track
from rich.status import Status
from rich.table import Table
from zipfile import ZipFile
from shutil import rmtree
from pathlib import Path
from .style import *
import tempfile
import requests
import json
import os

import platform
import ctypes

def documentPath():
    if platform.system() == 'Windows':
        # When on Windows, use the shell api to get the path
        CSIDL_PERSONAL = 5  # Code for 'My Documents'
        SHGFP_TYPE_CURRENT = 0  # Get current, not default value

        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)

        return buf.value
    else:
        # For Linux/Mac
        return os.path.expanduser('~/Documents')


# 从 url 下载 zip 并解压到 to
def downloadFile(url: str, to: Path):
	with tempfile.TemporaryDirectory() as tmp_dir:
		local_zip = os.path.join(tmp_dir, 'file.zip')
		with requests.get(url, stream=True) as r:
			r.raise_for_status()
			total_size_in_bytes = int(r.headers.get('content-length', 0)) if 'content-length' in r.headers else None
			block_size = 1024  # 1 Kibibyte
			progress_bar = Progress(transient=True)
			progress_task = progress_bar.add_task("[cyan]下载中...", total=total_size_in_bytes) if total_size_in_bytes else progress_bar.add_task("[cyan]下载中...", total=total_size_in_bytes, unknown=True)
			with progress_bar:
				with open(local_zip, 'wb') as f:
					for chunk in r.iter_content(block_size):
						f.write(chunk)
						progress_bar.update(progress_task, advance=len(chunk))
		with ZipFile(local_zip, 'r') as zip_ref:
			file_list = zip_ref.namelist()
			for file_name in track(file_list, description="[cyan]解压中...", transient=True):
				zip_ref.extract(member=file_name, path=to)

PLUGIN_INDEX = 'https://raw.githubusercontent.com/LiteLoaderQQNT/LiteLoaderQQNT-Plugin-List/v3/plugins.json'

import concurrent.futures

def fetch_plugins():
    # 更新单个插件 manifest
	def fetch_manifest(plugin):
		try:
			MANIFEST = f'https://raw.githubusercontent.com/{plugin["repo"]}/{plugin["branch"]}/manifest.json'
			manifest = requests.get(MANIFEST).json()
			return manifest['slug'], manifest
		except Exception as e:
			pass
	
	plugin_index = requests.get(PLUGIN_INDEX).json()
	plugins = {}
	progress_bar = Progress(transient=True)
	task = progress_bar.add_task('[cyan]更新插件列表中...', total=len(plugin_index))
	with progress_bar:
		with concurrent.futures.ThreadPoolExecutor() as executor:
			future_to_plugin = {executor.submit(fetch_manifest, plugin): plugin for plugin in plugin_index}
			for future in concurrent.futures.as_completed(future_to_plugin):
				plugin = future_to_plugin[future]
				try:
					slug, manifest = future.result() # type: ignore
					plugins[slug] = manifest
					progress_bar.update(task,advance=1)
				except Exception as e:
					pass
	return plugins


def load_plugins(plugins_folder: Path):
	plugins = {}
	for manifest in track(plugins_folder.glob('*/manifest.json'), description="[cyan]获取本地插件中...", transient=True):
		with open(manifest, 'r', encoding='utf-8') as f:
			manifest = json.load(f)
			plugins[manifest['slug']] = manifest
	return plugins

# 比较 x.y.z 格式的版本号
def version_less(a:str,b:str):
	return [int(i) for i in a.split('.')] < [int(i) for i in b.split('.')]

# 获取插件下载链接
def get_download_url(manifest: dict,version: str=''):
	repo = manifest['repository']['repo']
	branch = manifest['repository']['branch']
	use_release = manifest['repository'].get('use_release')
	tag = use_release.get('tag') if use_release else None
	name = use_release.get('name') if use_release else None
	if version:
		tag = version
	release_latest_url = f"https://github.com/{repo}/releases/{tag}/download/{name}" if tag and name else None
	release_tag_url = f"https://github.com/{repo}/releases/download/{tag}/{name}" if tag and name else None
	source_code_url = f"https://github.com/{repo}/archive/refs/heads/{branch}.zip"
	release_url = release_latest_url if tag == "latest" else release_tag_url
	url = release_url if use_release else source_code_url
	return '' if not url else url

# 安装插件
def add_plugin(plugins_folder: Path, manifest: dict, version=None):
	slug = manifest['slug']
	display_name = f'[bold]{manifest["name"]}@{version}[/bold]' if version else f'[bold]{manifest["name"]}@{manifest["version"]}[/bold]'
	print(f'[info]开始安装插件 {display_name}[/info]')
	url = get_download_url(manifest,version) if version else get_download_url(manifest)
	print(f'[info]从 {url} 获取插件...[/info]')

	if Path(plugins_folder / slug).exists():
		print('[info]切换版本：删除原有插件[/info]')
		rmtree(plugins_folder / slug)
 
	downloadFile(url, plugins_folder / slug)

	# 这一坨用于修复直接下载仓库 zip 造成的多套了一层目录的问题
	direct_download_path = plugins_folder / slug / f'{manifest["repository"]["repo"].split("/")[1]}-{manifest["repository"]["branch"]}'
	if not (plugins_folder / slug / 'manifest.json').exists() and (direct_download_path / 'manifest.json').exists():
		(plugins_folder / slug).rename(f'{plugins_folder / slug}-temp')
		(Path(f'{plugins_folder / slug}-temp') / f'{manifest["repository"]["repo"].split("/")[1]}-{manifest["repository"]["branch"]}').rename(plugins_folder / slug)
		Path(f'{plugins_folder / slug}-temp').rmdir()
  
	print(f'llpm: [cyan]插件 {display_name} 安装完成[/cyan]')
	if not (plugins_folder / slug / 'manifest.json').exists():
		print(f'[warning]warning:[/warning] 插件 {manifest["name"]} 安装成功，但是无法读取插件元数据')
		print(f'[warning]warning:[/warning] 这大概率是因为插件目录结构不规范，但也有可能是下载过程中出现错误')
		print(f'[warning]warning:[/warning] 可能不会影响 LiteLoader 加载插件，但是会影响 llpm 识别该插件')
		print(f'[warning]warning:[/warning] 你可以前往插件文件夹尝试手动修复，也可以使用 `llpm remove {manifest["slug"]} --force` 强制卸载该插件')
		print(f'[warning]warning:[/warning] 或使用 `llpm audit` 尝试自动修复')

# 卸载插件
def remove_plugin(plugins_folder: Path, manifest: dict):
	slug = manifest['slug']
	display_name = f'[bold]{manifest["name"]}@{manifest["version"]}[/bold]'
	if not (plugins_folder / slug).exists():
		print(f'[error]fetal:[/error] 插件 {manifest["name"]} 未安装')
		return
	print(f'[info]开始卸载插件 {display_name}[/info]')
	rmtree(plugins_folder / slug)
	print(f'llpm: [cyan]插件 {display_name} 卸载完成[/cyan]')

def merge_author(author: list):
    res = ""
    for elm in author:
        res += f"{elm['name']} "
    return res.strip()

# 列出插件列表
def list_plugins(plugins: dict, title: str):
	table = Table(title=title,show_lines=True)
	table.add_column('名称',justify='left',no_wrap=True,style="cyan bold")
	table.add_column('描述',justify='left')
	table.add_column('版本',justify='left',no_wrap=True)
	table.add_column('作者',justify='left',no_wrap=True,style="magenta")
	table.add_column('标识符',justify='left',no_wrap=True,style="green")
	for slug in plugins:
		author = merge_author(plugins[slug]['author']) if type(plugins[slug]['author']) == list else plugins[slug]['author']['name']
		table.add_row(f'[link=https://github.com/{plugins[slug]["repository"]["repo"]}]{plugins[slug]["name"]}[/link]',plugins[slug]['description'],plugins[slug]['version'],author,plugins[slug]['slug'])
	print(table)
	print(f'llpm: [info]共 {len(plugins)} 个插件[/info]')
	print('llpm: [info]使用 `llpm add <标识符>` 安装插件[/info]')

def validate_manifest(manifest: dict):
    return manifest.get('manifest_version',-1) == 3 and manifest.get('name') and manifest.get('slug') and manifest.get('version') and manifest.get('author') and manifest.get('repository') and manifest.get('platform') and manifest.get('injects')

# 检查并修复插件目录下可能存在的错误
def audit(plugins_folder: Path, fix: bool):
	error_cnt = 0
	need_rename,need_remove = [],[]
	with Status('[cyan]正在检查插件目录...[/cyan]') as status:
		# 元数据标识符与目录名不同步
		for manifest_path in plugins_folder.glob('**/manifest.json'):
			with open(manifest_path, 'r', encoding='utf-8') as f:
				manifest = json.load(f)
				if validate_manifest(manifest):
					if manifest_path.parent != plugins_folder / manifest['slug']:
						print(f'llpm: [warning]warning:[/warning] 插件 [bold][cyan]{manifest["name"]}({manifest["slug"]})[/cyan][/bold] 的元数据标识符与目录名不同步')
						error_cnt += 1
						need_rename.append((manifest_path.parent, plugins_folder / manifest['slug']))
		# 空目录
		for child_dictionary in plugins_folder.glob('*/'):
			if child_dictionary.is_dir() and len(list(child_dictionary.iterdir())) == 0:
				print(f'llpm: [warning]warning:[/warning] 检测到空目录 {child_dictionary}')
				error_cnt += 1
				need_remove.append(child_dictionary)
		print(f'llpm: [info]检查完成[/info]')
		if error_cnt and fix:
			print(f'llpm: [cyan]尝试自动修复 {error_cnt} 个错误...[/cyan]')
			status.update(f'[cyan]正在自动修复...[/cyan]')	
			for old_path, new_path in need_rename:
				try:
					print(f'llpm: [info]重命名 "{old_path}" 为 "{new_path}"[/info]')
					old_path.rename(new_path)
					error_cnt -= 1
				except Exception as e:
					print(f'llpm: [error]error:[/error] 修复失败')
					print(e)
					pass
			for path in need_remove:
				try:
					print(f'llpm: [info]删除目录 "{path}"[/info]')
					path.rmdir()
					error_cnt -= 1
				except Exception as e:
					print(f'llpm: [error]error:[/error] 修复失败')
					print(e)
					pass
			
	if error_cnt > 0:
		print(f'llpm: [warning]warning:[/warning] 审计模块检测到 {error_cnt} 个错误')
		if not fix:
			print(f'llpm: [warning]warning:[/warning] 可以使用命令 `llpm audit --fix` 来尝试自动修复这些错误')
		else:
			print(f'llpm: [error]error:[/error] 自动修复失败')
	else:
		print(f'llpm: [cyan]审计模块未检测到错误[/cyan]')