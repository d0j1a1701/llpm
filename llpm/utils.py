from rich.progress import Progress,track
from rich.table import Table
from zipfile import ZipFile
from shutil import rmtree
from pathlib import Path
from .style import *
import tempfile
import requests
import json
import os

# 从 url 下载 zip 并解压到 to
def downloadFile(url: str, to: Path):
	with tempfile.TemporaryDirectory() as tmp_dir:
		local_zip = os.path.join(tmp_dir, 'file.zip')
		with requests.get(url, stream=True) as r:
			r.raise_for_status()
			total_size_in_bytes = int(r.headers.get('content-length', 0)) if 'content-length' in r.headers else None
			block_size = 1024  # 1 Kibibyte
			progress_bar = Progress(transient=True)
			progress_task = progress_bar.add_task("[cyan]下载中...", total=total_size_in_bytes) if total_size_in_bytes else progress_bar.add_task("[cyan]Downloading...", total=total_size_in_bytes, unknown=True)
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


def load_plugins(plugin_folder: Path):
	plugins = {}
	for manifest in track(plugin_folder.glob('*/manifest.json'), description="[cyan]获取本地插件中...", transient=True):
		with open(manifest, 'r', encoding='utf-8') as f:
			manifest = json.load(f)
			plugins[manifest['slug']] = manifest
	return plugins

# 比较 x.y.z 格式的版本号
def version_less(a:str,b:str):
	return [int(i) for i in a.split('.')] < [int(i) for i in b.split('.')]

# 获取插件下载链接
def get_download_url(manifest: dict):
	repo = manifest['repository']['repo']
	branch = manifest['repository']['branch']
	use_release = manifest['repository']['use_release']
	tag = use_release.get('tag') if use_release else None
	name = use_release.get('name') if use_release else None
	release_latest_url = f"https://github.com/{repo}/releases/{tag}/download/{name}" if tag and name else None
	release_tag_url = f"https://github.com/{repo}/releases/download/{tag}/{name}" if tag and name else None
	source_code_url = f"https://github.com/{repo}/archive/refs/heads/{branch}.zip"
	release_url = release_latest_url if tag == "latest" else release_tag_url
	url = release_url if use_release else source_code_url
	return '' if not url else url

# 安装插件
def add_plugin(plugin_folder: Path, manifest: dict):
	slug = manifest['slug']
	display_name = f'[bold]{manifest["name"]} v{manifest["version"]}[/bold]'
	if (plugin_folder / slug).exists():
		print(f'[error]fetal:[/error] 插件 {manifest["name"]} 已安装')
		return
	print(f'[info]开始安装插件 {display_name}[/info]')
	url = get_download_url(manifest)
	print(f'[info]从 {url} 获取插件...[/info]')
	downloadFile(url, plugin_folder / slug)
	print(f'llpm: [cyan]插件 {display_name} 安装完成[/cyan]')

# 卸载插件
def remove_plugin(plugin_folder: Path, manifest: dict):
	slug = manifest['slug']
	display_name = f'[bold]{manifest["name"]} v{manifest["version"]}[/bold]'
	if not (plugin_folder / slug).exists():
		print(f'[error]fetal:[/error] 插件 {manifest["name"]} 未安装')
		return
	print(f'[info]开始卸载插件 {display_name}[/info]')
	rmtree(plugin_folder / slug)
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
		table.add_row(plugins[slug]['name'],plugins[slug]['description'],plugins[slug]['version'],author,plugins[slug]['slug'])
	print(table)
	print(f'llpm: [info]共 {len(plugins)} 个插件[/info]')
	print('llpm: [info]使用 `llpm add <标识符>` 安装插件[/info]')