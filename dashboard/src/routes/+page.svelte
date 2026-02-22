<script lang="ts">
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { analyticsApi, healthApi, projectsApi } from '$lib/api';
	import type { AnalyticsOverview, HealthStatus } from '$lib/api';

	let overview: AnalyticsOverview | null = null;
	let health: HealthStatus | null = null;
	let projectCount = 0;
	let loading = true;
	let error = '';

	onMount(async () => {
		try {
			const [ov, h, projs] = await Promise.allSettled([
				analyticsApi.overview(),
				healthApi.full(),
				projectsApi.list()
			]);
			if (ov.status === 'fulfilled') overview = ov.value;
			if (h.status === 'fulfilled') health = h.value;
			if (projs.status === 'fulfilled') projectCount = projs.value.length;
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Failed to load';
		} finally {
			loading = false;
		}
	});

	function fmtBytes(b: number) {
		if (!b) return '0 B';
		const k = 1024;
		const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
		const i = Math.floor(Math.log(b) / Math.log(k));
		return `${parseFloat((b / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
	}

	$: stats = [
		{
			label: 'Projects',
			value: projectCount ?? 0,
			icon: '◧',
			iconBg: 'bg-coco-900/50',
			iconColor: 'text-coco-400',
			href: `${base}/projects`
		},
		{
			label: 'Total Users',
			value: overview?.total_users ?? '—',
			icon: '◎',
			iconBg: 'bg-blue-900/50',
			iconColor: 'text-blue-400',
			href: `${base}/users`
		},
		{
			label: 'Total Documents',
			value: overview?.total_documents ?? '—',
			icon: '▤',
			iconBg: 'bg-purple-900/50',
			iconColor: 'text-purple-400',
			href: null
		},
		{
			label: 'Storage Used',
			value: overview?.total_storage_used ? fmtBytes(overview.total_storage_used as number) : '—',
			icon: '⬡',
			iconBg: 'bg-amber-900/50',
			iconColor: 'text-amber-400',
			href: null
		}
	];

	$: dbStatus = health?.database?.status ?? 'unknown';
	$: redisStatus = health?.redis?.status ?? 'unknown';
	$: systemOk = health?.status === 'healthy' || health?.status === 'ok';
</script>

<svelte:head>
	<title>Overview — CocoBase Dashboard</title>
</svelte:head>

<div class="p-6 max-w-7xl mx-auto space-y-6">
	<!-- Header -->
	<div>
		<h1 class="text-2xl font-bold text-white">Overview</h1>
		<p class="text-gray-500 text-sm mt-0.5">Your CocoBase platform at a glance</p>
	</div>

	{#if loading}
		<div class="flex items-center gap-3 text-gray-500 py-12">
			<span class="animate-spin text-xl">◌</span> Loading dashboard…
		</div>
	{:else if error}
		<div class="card text-red-400 text-sm">{error}</div>
	{:else}
		<!-- Stats grid -->
		<div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
			{#each stats as stat}
				<svelte:element
					this={stat.href ? 'a' : 'div'}
					href={stat.href}
					class="stat-card {stat.href ? 'hover:border-coco-700 cursor-pointer transition-colors' : ''}"
				>
					<div class="stat-icon {stat.iconBg} {stat.iconColor}">{stat.icon}</div>
					<div>
						<div class="text-2xl font-bold text-white">{stat.value}</div>
						<div class="text-xs text-gray-500 mt-0.5">{stat.label}</div>
					</div>
				</svelte:element>
			{/each}
		</div>

		<!-- Health & Quick Links -->
		<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
			<!-- System Health -->
			<div class="card lg:col-span-1">
				<h2 class="text-sm font-semibold text-gray-300 mb-4">System Health</h2>
				<div class="space-y-3">
					<div class="flex items-center justify-between">
						<span class="text-sm text-gray-400">API</span>
						<span class="badge {systemOk ? 'badge-green' : 'badge-red'}">
							{systemOk ? 'healthy' : health?.status ?? 'unknown'}
						</span>
					</div>
					<div class="flex items-center justify-between">
						<span class="text-sm text-gray-400">Database</span>
						<span
							class="badge {dbStatus === 'healthy' || dbStatus === 'ok'
								? 'badge-green'
								: 'badge-red'}"
						>
							{dbStatus}
						</span>
					</div>
					<div class="flex items-center justify-between">
						<span class="text-sm text-gray-400">Redis</span>
						<span
							class="badge {redisStatus === 'healthy' || redisStatus === 'ok'
								? 'badge-green'
								: 'badge-red'}"
						>
							{redisStatus}
						</span>
					</div>
					{#if health?.system}
						<div class="pt-2 border-t border-gray-800 space-y-2">
							<div>
								<div class="flex justify-between text-xs text-gray-500 mb-1">
									<span>CPU</span>
									<span>{health.system.cpu_percent.toFixed(1)}%</span>
								</div>
								<div class="h-1.5 bg-gray-800 rounded-full overflow-hidden">
									<div
										class="h-full bg-coco-500 rounded-full"
										style="width: {Math.min(health.system.cpu_percent, 100)}%"
									></div>
								</div>
							</div>
							<div>
								<div class="flex justify-between text-xs text-gray-500 mb-1">
									<span>Memory</span>
									<span>{health.system.memory_percent.toFixed(1)}%</span>
								</div>
								<div class="h-1.5 bg-gray-800 rounded-full overflow-hidden">
									<div
										class="h-full bg-blue-500 rounded-full"
										style="width: {Math.min(health.system.memory_percent, 100)}%"
									></div>
								</div>
							</div>
						</div>
					{/if}
				</div>
			</div>

			<!-- Quick access -->
			<div class="card lg:col-span-2">
				<h2 class="text-sm font-semibold text-gray-300 mb-4">Quick Access</h2>
				<div class="grid grid-cols-2 gap-2">
					{#each [
						{ label: 'Manage Projects', href: `${base}/projects`, icon: '◧', desc: 'Create and configure projects' },
						{ label: 'Browse Users', href: `${base}/users`, icon: '◎', desc: 'View registered app users' },
						{ label: 'Health Monitor', href: `${base}/health`, icon: '◈', desc: 'System and service status' },
						{ label: 'API Docs', href: '/_/docs', icon: '⊞', desc: 'Full dashboard API reference' }
					] as link}
						<a
							href={link.href}
							class="flex items-start gap-3 p-3 rounded-lg border border-gray-800 hover:border-coco-700 hover:bg-gray-800/50 transition-all group"
						>
							<span class="text-coco-400 text-lg mt-0.5">{link.icon}</span>
							<div>
								<div class="text-sm font-medium text-gray-200 group-hover:text-white transition-colors">
									{link.label}
								</div>
								<div class="text-xs text-gray-600">{link.desc}</div>
							</div>
						</a>
					{/each}
				</div>
			</div>
		</div>
	{/if}
</div>
