<script lang="ts">
	import { onMount } from 'svelte';
	import { usersApi } from '$lib/api';
	import type { AppUser } from '$lib/api';
	import { showToast } from '$lib/stores';

	let users: AppUser[] = [];
	let loading = true;
	let offset = 0;
	const limit = 50;

	onMount(() => load());

	async function load() {
		loading = true;
		try {
			users = await usersApi.list({ limit, offset });
		} catch (e: unknown) {
			showToast(e instanceof Error ? e.message : 'Failed to load users', 'error');
		} finally {
			loading = false;
		}
	}

	function fmtDate(d: string) {
		return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
	}

	function avatar(u: AppUser) {
		return (u.username ?? u.email ?? '?')[0].toUpperCase();
	}
</script>

<svelte:head>
	<title>Users — CocoBase Dashboard</title>
</svelte:head>

<div class="p-6 max-w-5xl mx-auto space-y-6">
	<div>
		<h1 class="text-2xl font-bold text-white">App Users</h1>
		<p class="text-gray-500 text-sm mt-0.5">Users registered via the auth collections API</p>
	</div>

	{#if loading}
		<div class="flex items-center gap-3 text-gray-500 py-12">
			<span class="animate-spin text-xl">◌</span> Loading users…
		</div>
	{:else if users.length === 0}
		<div class="card text-center py-16">
			<div class="text-5xl mb-4 text-gray-700">◎</div>
			<p class="text-gray-500">No users registered yet.</p>
		</div>
	{:else}
		<div class="flex items-center justify-between mb-2">
			<p class="text-sm text-gray-500">{users.length} users</p>
		</div>

		<div class="table-wrapper">
			<table>
				<thead>
					<tr>
						<th>User</th>
						<th>Email</th>
						<th>Verified</th>
						<th>Joined</th>
					</tr>
				</thead>
				<tbody>
					{#each users as user}
						<tr>
							<td>
								<div class="flex items-center gap-3">
									<div
										class="w-8 h-8 rounded-full bg-coco-900 border border-coco-800 flex items-center justify-center text-coco-300 text-xs font-bold flex-shrink-0"
									>
										{avatar(user)}
									</div>
									<span class="font-medium text-gray-200">
										{user.username ?? '—'}
									</span>
								</div>
							</td>
							<td class="text-gray-400">{user.email}</td>
							<td>
								{#if user.confirmed_email}
									<span class="badge badge-green">verified</span>
								{:else}
									<span class="badge badge-gray">unverified</span>
								{/if}
							</td>
							<td class="text-gray-500 text-xs">{fmtDate(user.created_at)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
