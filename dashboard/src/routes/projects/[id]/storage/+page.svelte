<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { storageApi } from '$lib/api';
	import type { StorageFile, StorageInfo } from '$lib/api';
	import { showToast } from '$lib/stores';

	$: projectId = $page.params.id;

	let files: StorageFile[] = [];
	let info: StorageInfo | null = null;
	let loading = true;
	let uploading = false;
	let fileInput: HTMLInputElement;

	onMount(() => load());

	async function load() {
		loading = true;
		try {
			const [f, i] = await Promise.allSettled([
				storageApi.list(projectId),
				storageApi.info(projectId)
			]);
			if (f.status === 'fulfilled') files = f.value;
			if (i.status === 'fulfilled') info = i.value;
		} catch (e: unknown) {
			showToast(e instanceof Error ? e.message : 'Failed to load', 'error');
		} finally {
			loading = false;
		}
	}

	async function upload(e: Event) {
		const input = e.target as HTMLInputElement;
		if (!input.files?.length) return;
		uploading = true;
		const fd = new FormData();
		for (const file of Array.from(input.files)) {
			fd.append('file', file);
		}
		try {
			await storageApi.upload(projectId, fd);
			showToast('Upload successful!', 'success');
			await load();
		} catch (e: unknown) {
			showToast(e instanceof Error ? e.message : 'Upload failed', 'error');
		} finally {
			uploading = false;
			input.value = '';
		}
	}

	async function deleteFile(id: string, name: string) {
		if (!confirm(`Delete "${name}"?`)) return;
		try {
			await storageApi.delete(projectId, id);
			files = files.filter((f) => f.id !== id);
			showToast('File deleted', 'success');
		} catch (e: unknown) {
			showToast(e instanceof Error ? e.message : 'Failed to delete', 'error');
		}
	}

	function fmtBytes(b: number) {
		if (!b) return '0 B';
		const k = 1024;
		const sizes = ['B', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(b) / Math.log(k));
		return `${parseFloat((b / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
	}

	function fmtDate(d: string) {
		return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
	}

	function fileIcon(type: string) {
		if (type.startsWith('image/')) return '🖼';
		if (type.startsWith('video/')) return '🎬';
		if (type.startsWith('audio/')) return '🎵';
		if (type.includes('pdf')) return '📄';
		return '📁';
	}

	$: usedPct = info ? Math.min((info.used / info.limit) * 100, 100) : 0;
</script>

<svelte:head>
	<title>Storage — CocoBase Dashboard</title>
</svelte:head>

<div class="p-6 max-w-5xl mx-auto space-y-6">
	<div class="flex items-center gap-2 text-sm text-gray-500">
		<a href="{base}/projects" class="hover:text-gray-300">Projects</a>
		<span>›</span>
		<a href="{base}/projects/{projectId}" class="hover:text-gray-300">Project</a>
		<span>›</span>
		<span class="text-gray-300">Storage</span>
	</div>

	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-bold text-white">Storage</h1>
			{#if info}
				<p class="text-gray-500 text-sm mt-0.5">
					{fmtBytes(info.used)} / {fmtBytes(info.limit)} used · {info.file_count} files
				</p>
			{/if}
		</div>
		<button
			class="btn btn-primary"
			disabled={uploading}
			on:click={() => fileInput.click()}
		>
			{uploading ? '⟳ Uploading…' : '↑ Upload'}
		</button>
		<input bind:this={fileInput} type="file" multiple class="hidden" on:change={upload} />
	</div>

	<!-- Usage bar -->
	{#if info}
		<div class="card">
			<div class="flex justify-between text-xs text-gray-400 mb-2">
				<span>Storage usage</span>
				<span>{usedPct.toFixed(1)}%</span>
			</div>
			<div class="h-2 bg-gray-800 rounded-full overflow-hidden">
				<div
					class="h-full rounded-full transition-all {usedPct > 90 ? 'bg-red-500' : usedPct > 70 ? 'bg-amber-500' : 'bg-coco-500'}"
					style="width: {usedPct}%"
				></div>
			</div>
		</div>
	{/if}

	{#if loading}
		<div class="flex items-center gap-3 text-gray-500 py-12">
			<span class="animate-spin text-xl">◌</span> Loading files…
		</div>
	{:else if files.length === 0}
		<div class="card text-center py-16">
			<div class="text-5xl mb-4">📂</div>
			<p class="text-gray-500">No files uploaded yet.</p>
		</div>
	{:else}
		<div class="table-wrapper">
			<table>
				<thead>
					<tr>
						<th>Name</th>
						<th>Type</th>
						<th>Size</th>
						<th>Uploaded</th>
						<th></th>
					</tr>
				</thead>
				<tbody>
					{#each files as file}
						<tr>
							<td>
								<div class="flex items-center gap-2">
									<span>{fileIcon(file.content_type)}</span>
									<a
										href={file.url}
										target="_blank"
										rel="noopener"
										class="text-coco-400 hover:text-coco-300 text-sm truncate max-w-xs"
									>
										{file.name}
									</a>
								</div>
							</td>
							<td><span class="badge badge-gray text-[10px]">{file.content_type.split('/')[1] ?? file.content_type}</span></td>
							<td class="text-gray-500 text-xs">{fmtBytes(file.size)}</td>
							<td class="text-gray-500 text-xs">{fmtDate(file.created_at)}</td>
							<td>
								<button
									class="btn btn-ghost text-red-500 hover:text-red-300 text-xs"
									on:click={() => deleteFile(file.id, file.name)}
								>
									Delete
								</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
