<script lang="ts">
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { projectsApi } from '$lib/api';
	import type { Project } from '$lib/api';
	import { showToast } from '$lib/stores';

	let projects: Project[] = [];
	let loading = true;
	let creating = false;
	let showCreateForm = false;
	let newName = '';
	let newDesc = '';

	onMount(load);

	async function load() {
		loading = true;
		try {
			projects = await projectsApi.list();
		} catch (e: unknown) {
			showToast(e instanceof Error ? e.message : 'Failed to load projects', 'error');
		} finally {
			loading = false;
		}
	}

	async function createProject() {
		if (!newName.trim()) return;
		creating = true;
		try {
			const p = await projectsApi.create({ name: newName.trim(), description: newDesc.trim() || undefined });
			projects = [p, ...projects];
			showCreateForm = false;
			newName = '';
			newDesc = '';
			showToast('Project created!', 'success');
		} catch (e: unknown) {
			showToast(e instanceof Error ? e.message : 'Failed to create project', 'error');
		} finally {
			creating = false;
		}
	}

	async function deleteProject(id: string, name: string) {
		if (!confirm(`Delete project "${name}"? This cannot be undone.`)) return;
		try {
			await projectsApi.delete(id);
			projects = projects.filter((p) => p.id !== id);
			showToast('Project deleted', 'success');
		} catch (e: unknown) {
			showToast(e instanceof Error ? e.message : 'Failed to delete', 'error');
		}
	}

	function fmtDate(d: string) {
		return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
	}
</script>

<svelte:head>
	<title>Projects — CocoBase Dashboard</title>
</svelte:head>

<div class="p-6 max-w-5xl mx-auto space-y-6">
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-bold text-white">Projects</h1>
			<p class="text-gray-500 text-sm mt-0.5">{projects.length} project{projects.length !== 1 ? 's' : ''}</p>
		</div>
		<button class="btn btn-primary" on:click={() => (showCreateForm = !showCreateForm)}>
			+ New Project
		</button>
	</div>

	{#if showCreateForm}
		<form
			on:submit|preventDefault={createProject}
			class="card border-coco-700 space-y-4"
		>
			<h2 class="text-sm font-semibold text-gray-300">Create Project</h2>
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<div>
					<label class="label" for="proj-name">Name *</label>
					<input
						id="proj-name"
						type="text"
						bind:value={newName}
						class="input"
						placeholder="My App"
						required
						disabled={creating}
					/>
				</div>
				<div>
					<label class="label" for="proj-desc">Description</label>
					<input
						id="proj-desc"
						type="text"
						bind:value={newDesc}
						class="input"
						placeholder="Optional"
						disabled={creating}
					/>
				</div>
			</div>
			<div class="flex gap-2">
				<button type="submit" class="btn btn-primary" disabled={creating || !newName.trim()}>
					{creating ? 'Creating…' : 'Create'}
				</button>
				<button
					type="button"
					class="btn btn-secondary"
					on:click={() => (showCreateForm = false)}
					disabled={creating}
				>
					Cancel
				</button>
			</div>
		</form>
	{/if}

	{#if loading}
		<div class="flex items-center gap-3 text-gray-500 py-12">
			<span class="animate-spin text-xl">◌</span> Loading…
		</div>
	{:else if projects.length === 0}
		<div class="card text-center py-16">
			<div class="text-5xl mb-4 text-gray-700">◧</div>
			<p class="text-gray-500">No projects yet. Create your first one above.</p>
		</div>
	{:else}
		<div class="grid gap-3">
			{#each projects as project}
				<div class="card flex items-start justify-between hover:border-gray-700 transition-colors">
					<div class="flex items-start gap-4">
						<div
							class="w-10 h-10 rounded-lg bg-coco-900/60 border border-coco-800 flex items-center justify-center text-coco-400 font-bold text-lg flex-shrink-0"
						>
							{project.name[0].toUpperCase()}
						</div>
						<div>
							<a
								href="{base}/projects/{project.id}"
								class="text-base font-semibold text-gray-100 hover:text-coco-300 transition-colors"
							>
								{project.name}
							</a>
							{#if project.description}
								<p class="text-sm text-gray-500 mt-0.5">{project.description}</p>
							{/if}
							<p class="text-xs text-gray-600 mt-1">Created {fmtDate(project.created_at)}</p>
						</div>
					</div>
					<div class="flex items-center gap-2 flex-shrink-0 ml-4">
						<a href="{base}/projects/{project.id}" class="btn btn-secondary text-xs">Open →</a>
						<button
							class="btn btn-ghost text-red-500 hover:text-red-300 text-xs"
							on:click={() => deleteProject(project.id, project.name)}
						>
							Delete
						</button>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
