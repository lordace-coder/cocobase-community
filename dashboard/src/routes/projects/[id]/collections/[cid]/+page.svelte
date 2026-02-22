<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { collectionsApi } from '$lib/api';
	import { showToast } from '$lib/stores';

	$: projectId = $page.params.id;
	$: collectionId = $page.params.cid;

	let documents: Record<string, unknown>[] = [];
	let columns: string[] = [];
	let total = 0;
	let loading = true;
	let limit = 25;
	let offset = 0;
	let search = '';
	let deleting: string | null = null;

	onMount(() => load());
	$: collectionId && load();

	async function load() {
		loading = true;
		try {
			const res = await collectionsApi.documents(collectionId, { limit, offset });
			documents = Array.isArray(res) ? res : (res.data ?? []);
			total = (res as { total?: number }).total ?? documents.length;
			// Derive columns from first document
			if (documents.length > 0) {
				const all = new Set<string>();
				documents.forEach((d) => Object.keys(d).forEach((k) => all.add(k)));
				// put id first, then the rest alphabetically
				const sorted = Array.from(all).sort((a, b) => {
					if (a === 'id') return -1;
					if (b === 'id') return 1;
					if (a === 'created_at') return 1;
					if (b === 'created_at') return -1;
					return a.localeCompare(b);
				});
				columns = sorted.slice(0, 8); // max 8 columns to avoid overflow
			}
		} catch (e: unknown) {
			showToast(e instanceof Error ? e.message : 'Failed to load', 'error');
		} finally {
			loading = false;
		}
	}

	async function deleteDoc(docId: string) {
		if (!confirm('Delete this document?')) return;
		deleting = docId;
		try {
			await collectionsApi.deleteDocument(collectionId, docId);
			documents = documents.filter((d) => d.id !== docId);
			total = Math.max(0, total - 1);
			showToast('Document deleted', 'success');
		} catch (e: unknown) {
			showToast(e instanceof Error ? e.message : 'Failed to delete', 'error');
		} finally {
			deleting = null;
		}
	}

	function prev() {
		offset = Math.max(0, offset - limit);
		load();
	}

	function next() {
		offset = offset + limit;
		load();
	}

	function cellValue(val: unknown): string {
		if (val === null || val === undefined) return '—';
		if (typeof val === 'object') return JSON.stringify(val).slice(0, 60);
		const s = String(val);
		return s.length > 60 ? s.slice(0, 60) + '…' : s;
	}

	function isDate(key: string) {
		return key === 'created_at' || key === 'updated_at';
	}

	function fmtDate(v: unknown) {
		if (!v) return '—';
		try {
			return new Date(String(v)).toLocaleDateString('en-US', {
				month: 'short', day: 'numeric', year: 'numeric'
			});
		} catch {
			return String(v);
		}
	}
</script>

<svelte:head>
	<title>Collection — CocoBase Dashboard</title>
</svelte:head>

<div class="p-6 max-w-full space-y-5">
	<!-- Breadcrumb -->
	<div class="flex items-center gap-2 text-sm text-gray-500">
		<a href="{base}/projects" class="hover:text-gray-300">Projects</a>
		<span>›</span>
		<a href="{base}/projects/{projectId}" class="hover:text-gray-300">Project</a>
		<span>›</span>
		<span class="text-gray-300">Collection</span>
	</div>

	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-xl font-bold text-white font-mono text-sm bg-gray-800 px-3 py-1 rounded-lg inline-block">
				{collectionId}
			</h1>
			<p class="text-gray-500 text-sm mt-1">{total} document{total !== 1 ? 's' : ''}</p>
		</div>
	</div>

	{#if loading}
		<div class="flex items-center gap-3 text-gray-500 py-12">
			<span class="animate-spin text-xl">◌</span> Loading documents…
		</div>
	{:else if documents.length === 0}
		<div class="card text-center py-16 text-gray-600">
			No documents in this collection.
		</div>
	{:else}
		<div class="table-wrapper">
			<table>
				<thead>
					<tr>
						{#each columns as col}
							<th>{col}</th>
						{/each}
						<th></th>
					</tr>
				</thead>
				<tbody>
					{#each documents as doc}
						<tr>
							{#each columns as col}
								<td class="max-w-xs">
									{#if col === 'id'}
										<code class="text-xs text-gray-400">{cellValue(doc[col])}</code>
									{:else if isDate(col)}
										<span class="text-xs text-gray-500">{fmtDate(doc[col])}</span>
									{:else}
										<span class="text-sm">{cellValue(doc[col])}</span>
									{/if}
								</td>
							{/each}
							<td>
								<button
									class="btn btn-ghost text-red-500 hover:text-red-300 text-xs"
									disabled={deleting === String(doc.id)}
									on:click={() => deleteDoc(String(doc.id))}
								>
									{deleting === String(doc.id) ? '…' : 'Delete'}
								</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		<!-- Pagination -->
		<div class="flex items-center justify-between text-sm text-gray-500">
			<span>
				Showing {offset + 1}–{Math.min(offset + documents.length, total)} of {total}
			</span>
			<div class="flex gap-2">
				<button class="btn btn-secondary text-xs" disabled={offset === 0} on:click={prev}>← Prev</button>
				<button class="btn btn-secondary text-xs" disabled={offset + limit >= total} on:click={next}>Next →</button>
			</div>
		</div>
	{/if}
</div>
