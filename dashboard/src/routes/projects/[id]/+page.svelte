<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { projectsApi, keysApi, collectionsApi } from '$lib/api';
	import type { Project, Collection, OrmKey } from '$lib/api';
	import { showToast } from '$lib/stores';

	$: projectId = $page.params.id;

	let project: Project | null = null;
	let collections: Collection[] = [];
	let keys: OrmKey[] = [];
	let loading = true;
	let newKeyName = '';
	let creatingKey = false;
	let showKey: string | null = null;

	onMount(() => load());
	$: projectId && load();

	async function load() {
		loading = true;
		try {
			const [p, cols, ks] = await Promise.allSettled([
				projectsApi.get(projectId),
				projectsApi.collections(projectId),
				keysApi.list(projectId)
			]);
			if (p.status === 'fulfilled') project = p.value;
			if (cols.status === 'fulfilled') collections = cols.value;
			if (ks.status === 'fulfilled') keys = ks.value;
		} catch (e: unknown) {
			showToast(e instanceof Error ? e.message : 'Failed to load', 'error');
		} finally {
			loading = false;
		}
	}

	async function createKey() {
		if (!newKeyName.trim()) return;
		creatingKey = true;
		try {
			const k = await keysApi.create(projectId, { name: newKeyName.trim() });
			keys = [k, ...keys];
			showKey = k.key;
			newKeyName = '';
			showToast('API key created!', 'success');
		} catch (e: unknown) {
			showToast(e instanceof Error ? e.message : 'Failed to create key', 'error');
		} finally {
			creatingKey = false;
		}
	}

	async function deleteKey(keyId: string) {
		if (!confirm('Delete this API key? It cannot be recovered.')) return;
		try {
			await keysApi.delete(projectId, keyId);
			keys = keys.filter((k) => k.id !== keyId);
			showToast('Key deleted', 'success');
		} catch (e: unknown) {
			showToast(e instanceof Error ? e.message : 'Failed to delete', 'error');
		}
	}

	function copyKey(key: string) {
		navigator.clipboard.writeText(key).then(() => showToast('Copied!', 'success'));
	}

	function fmtDate(d: string) {
		return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
	}
</script>

<svelte:head>
	<title>{project?.name ?? 'Project'} — CocoBase Dashboard</title>
</svelte:head>

<div class="p-6 max-w-6xl mx-auto space-y-6">
	<!-- Breadcrumb -->
	<div class="flex items-center gap-2 text-sm text-gray-500">
		<a href="{base}/projects" class="hover:text-gray-300 transition-colors">Projects</a>
		<span>›</span>
		<span class="text-gray-300">{project?.name ?? '…'}</span>
	</div>

	{#if loading}
		<div class="flex items-center gap-3 text-gray-500 py-12">
			<span class="animate-spin text-xl">◌</span> Loading project…
		</div>
	{:else if project}
		<div class="flex items-start justify-between">
			<div>
				<h1 class="text-2xl font-bold text-white">{project.name}</h1>
				{#if project.description}
					<p class="text-gray-500 text-sm mt-0.5">{project.description}</p>
				{/if}
				<p class="text-xs text-gray-600 mt-1">ID: <code class="text-gray-400">{project.id}</code> · Created {fmtDate(project.created_at)}</p>
			</div>
			<div class="flex gap-2">
				<a href="{base}/projects/{projectId}/storage" class="btn btn-secondary text-sm">Storage</a>
				<a href="{base}/projects/{projectId}/settings" class="btn btn-secondary text-sm">Settings</a>
			</div>
		</div>

		<!-- Collections -->
		<section>
			<div class="flex items-center justify-between mb-3">
				<h2 class="text-base font-semibold text-gray-200">Collections</h2>
				<span class="badge badge-gray">{collections.length}</span>
			</div>
			{#if collections.length === 0}
				<div class="card text-center py-10 text-gray-600">
					No collections yet. Create one via the API or SDK.
				</div>
			{:else}
				<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
					{#each collections as col}
						<a
							href="{base}/projects/{projectId}/collections/{col.id}"
							class="card hover:border-coco-700 hover:bg-gray-800/30 transition-all cursor-pointer"
						>
							<div class="flex items-start gap-3">
								<div class="w-9 h-9 rounded-lg bg-purple-900/40 border border-purple-800 flex items-center justify-center text-purple-400 flex-shrink-0">
									▤
								</div>
								<div class="min-w-0">
									<div class="text-sm font-semibold text-gray-100 truncate">{col.name}</div>
									<div class="text-xs text-gray-500 mt-0.5">{fmtDate(col.created_at)}</div>
								</div>
							</div>
						</a>
					{/each}
				</div>
			{/if}
		</section>

		<!-- API Keys -->
		<section>
			<div class="flex items-center justify-between mb-3">
				<h2 class="text-base font-semibold text-gray-200">API Keys</h2>
			</div>

			<!-- New key form -->
			{#if showKey}
				<div class="card border-green-800 bg-green-950/30 mb-4">
					<p class="text-green-300 text-sm font-medium mb-2">
						⚠ Copy this key now — it won't be shown again.
					</p>
					<div class="flex items-center gap-2">
						<code class="flex-1 text-xs bg-gray-900 border border-gray-700 rounded px-3 py-2 text-green-300 break-all">
							{showKey}
						</code>
						<button class="btn btn-secondary text-xs flex-shrink-0" on:click={() => copyKey(showKey ?? '')}>Copy</button>
					</div>
					<button class="btn btn-ghost text-xs mt-2" on:click={() => (showKey = null)}>Dismiss</button>
				</div>
			{/if}

			<form on:submit|preventDefault={createKey} class="flex gap-2 mb-4">
				<input
					type="text"
					bind:value={newKeyName}
					class="input flex-1"
					placeholder="Key name (e.g. production)"
					disabled={creatingKey}
				/>
				<button type="submit" class="btn btn-primary flex-shrink-0" disabled={creatingKey || !newKeyName.trim()}>
					{creatingKey ? '…' : '+ Create Key'}
				</button>
			</form>

			{#if keys.length === 0}
				<div class="card text-center py-8 text-gray-600 text-sm">No API keys yet.</div>
			{:else}
				<div class="table-wrapper">
					<table>
						<thead>
							<tr>
								<th>Name</th>
								<th>Key (preview)</th>
								<th>Created</th>
								<th></th>
							</tr>
						</thead>
						<tbody>
							{#each keys as key}
								<tr>
									<td class="font-medium text-gray-200">{key.name}</td>
									<td>
										<code class="text-xs text-gray-400">
											{key.key.slice(0, 12)}••••••••••••
										</code>
									</td>
									<td class="text-gray-500">{fmtDate(key.created_at)}</td>
									<td>
										<button
											class="btn btn-ghost text-red-500 hover:text-red-300 text-xs"
											on:click={() => deleteKey(key.id)}
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
		</section>
	{/if}
</div>
