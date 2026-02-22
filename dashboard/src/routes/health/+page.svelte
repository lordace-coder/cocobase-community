<script lang="ts">
	import { onMount } from 'svelte';
	import { healthApi } from '$lib/api';
	import type { HealthStatus } from '$lib/api';
	import { showToast } from '$lib/stores';

	let health: HealthStatus | null = null;
	let loading = true;
	let refreshing = false;
	let lastChecked = '';

	onMount(() => load());

	async function load(refresh = false) {
		if (refresh) refreshing = true;
		else loading = true;
		try {
			health = await healthApi.full();
			lastChecked = new Date().toLocaleTimeString();
		} catch (e: unknown) {
			showToast(e instanceof Error ? e.message : 'Health check failed', 'error');
		} finally {
			loading = false;
			refreshing = false;
		}
	}

	function statusColor(status: string) {
		if (status === 'healthy' || status === 'ok' || status === 'connected') return 'badge-green';
		if (status === 'degraded') return 'badge-blue';
		return 'badge-red';
	}

	$: raw = health ? JSON.stringify(health, null, 2) : '';
</script>

<svelte:head>
	<title>Health — CocoBase Dashboard</title>
</svelte:head>

<div class="p-6 max-w-4xl mx-auto space-y-6">
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-bold text-white">System Health</h1>
			{#if lastChecked}
				<p class="text-gray-500 text-sm mt-0.5">Last checked at {lastChecked}</p>
			{/if}
		</div>
		<button
			class="btn btn-secondary"
			disabled={refreshing}
			on:click={() => load(true)}
		>
			{refreshing ? '⟳ Refreshing…' : '⟳ Refresh'}
		</button>
	</div>

	{#if loading}
		<div class="flex items-center gap-3 text-gray-500 py-12">
			<span class="animate-spin text-xl">◌</span> Checking health…
		</div>
	{:else if health}
		<!-- Status overview -->
		<div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
			<div class="card text-center">
				<div class="text-2xl mb-1">🟢</div>
				<div class="text-sm font-medium text-gray-300">API</div>
				<span class="badge {statusColor(health.status ?? 'unknown')} mt-1">
					{health.status ?? 'unknown'}
				</span>
			</div>
			{#if health.database}
				<div class="card text-center">
					<div class="text-2xl mb-1">🗄</div>
					<div class="text-sm font-medium text-gray-300">Database</div>
					<span class="badge {statusColor(health.database.status)} mt-1">
						{health.database.status}
					</span>
				</div>
			{/if}
			{#if health.redis}
				<div class="card text-center">
					<div class="text-2xl mb-1">⚡</div>
					<div class="text-sm font-medium text-gray-300">Redis</div>
					<span class="badge {statusColor(health.redis.status)} mt-1">
						{health.redis.status}
					</span>
				</div>
			{/if}
		</div>

		<!-- System resources -->
		{#if health.system}
			<div class="card space-y-4">
				<h2 class="text-sm font-semibold text-gray-300">System Resources</h2>
				<div>
					<div class="flex justify-between text-xs text-gray-400 mb-1.5">
						<span>CPU Usage</span>
						<span class="font-mono">{health.system.cpu_percent.toFixed(1)}%</span>
					</div>
					<div class="h-2 bg-gray-800 rounded-full overflow-hidden">
						<div
							class="h-full rounded-full transition-all duration-500 {health.system.cpu_percent > 90 ? 'bg-red-500' : health.system.cpu_percent > 70 ? 'bg-amber-500' : 'bg-coco-500'}"
							style="width: {Math.min(health.system.cpu_percent, 100)}%"
						></div>
					</div>
				</div>
				<div>
					<div class="flex justify-between text-xs text-gray-400 mb-1.5">
						<span>Memory Usage</span>
						<span class="font-mono">{health.system.memory_percent.toFixed(1)}%</span>
					</div>
					<div class="h-2 bg-gray-800 rounded-full overflow-hidden">
						<div
							class="h-full rounded-full transition-all duration-500 {health.system.memory_percent > 90 ? 'bg-red-500' : health.system.memory_percent > 70 ? 'bg-amber-500' : 'bg-blue-500'}"
							style="width: {Math.min(health.system.memory_percent, 100)}%"
						></div>
					</div>
				</div>
			</div>
		{/if}

		<!-- Raw JSON -->
		<details class="card">
			<summary class="text-sm text-gray-400 cursor-pointer select-none hover:text-gray-200 transition-colors">
				Raw health response
			</summary>
			<pre class="mt-4 text-xs text-gray-400 overflow-x-auto leading-relaxed">{raw}</pre>
		</details>
	{/if}
</div>
