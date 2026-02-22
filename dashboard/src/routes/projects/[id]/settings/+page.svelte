<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { emailApi } from '$lib/api';
	import type { SmtpConfig } from '$lib/api';
	import { showToast } from '$lib/stores';

	$: projectId = $page.params.id;

	let smtp: SmtpConfig | null = null;
	let loading = true;
	let saving = false;
	let testing = false;

	// Editable form
	let host = '';
	let port = 587;
	let username = '';
	let password = '';
	let fromEmail = '';
	let fromName = '';
	let useTls = true;

	onMount(() => load());

	async function load() {
		loading = true;
		try {
			smtp = await emailApi.getSmtp(projectId);
			host = smtp.host ?? '';
			port = smtp.port ?? 587;
			username = smtp.username ?? '';
			fromEmail = smtp.from_email ?? '';
			fromName = smtp.from_name ?? '';
			useTls = smtp.use_tls ?? true;
		} catch {
			// No SMTP config yet — that's fine
		} finally {
			loading = false;
		}
	}

	async function save() {
		saving = true;
		try {
			const payload: Partial<SmtpConfig> = {
				host, port, username, from_email: fromEmail,
				from_name: fromName || undefined, use_tls: useTls
			};
			if (password) payload.password = password;
			await emailApi.updateSmtp(projectId, payload);
			showToast('SMTP settings saved!', 'success');
			password = '';
		} catch (e: unknown) {
			showToast(e instanceof Error ? e.message : 'Save failed', 'error');
		} finally {
			saving = false;
		}
	}

	async function testSmtp() {
		testing = true;
		try {
			const res = await emailApi.testSmtp(projectId);
			showToast(res.message ?? (res.success ? 'SMTP test passed!' : 'SMTP test failed'), res.success ? 'success' : 'error');
		} catch (e: unknown) {
			showToast(e instanceof Error ? e.message : 'Test failed', 'error');
		} finally {
			testing = false;
		}
	}
</script>

<svelte:head>
	<title>Settings — CocoBase Dashboard</title>
</svelte:head>

<div class="p-6 max-w-2xl mx-auto space-y-6">
	<div class="flex items-center gap-2 text-sm text-gray-500">
		<a href="{base}/projects" class="hover:text-gray-300">Projects</a>
		<span>›</span>
		<a href="{base}/projects/{projectId}" class="hover:text-gray-300">Project</a>
		<span>›</span>
		<span class="text-gray-300">Settings</span>
	</div>

	<h1 class="text-2xl font-bold text-white">Project Settings</h1>

	{#if loading}
		<div class="flex items-center gap-3 text-gray-500 py-12">
			<span class="animate-spin text-xl">◌</span> Loading…
		</div>
	{:else}
		<!-- SMTP Card -->
		<div class="card space-y-5">
			<div>
				<h2 class="text-base font-semibold text-gray-200">SMTP / Email</h2>
				<p class="text-sm text-gray-500 mt-0.5">Configure outbound email for this project</p>
			</div>

			<form on:submit|preventDefault={save} class="space-y-4">
				<div class="grid grid-cols-2 gap-4">
					<div>
						<label class="label" for="smtp-host">SMTP Host</label>
						<input id="smtp-host" type="text" bind:value={host} class="input" placeholder="smtp.gmail.com" />
					</div>
					<div>
						<label class="label" for="smtp-port">Port</label>
						<input id="smtp-port" type="number" bind:value={port} class="input" placeholder="587" />
					</div>
				</div>

				<div class="grid grid-cols-2 gap-4">
					<div>
						<label class="label" for="smtp-user">Username</label>
						<input id="smtp-user" type="text" bind:value={username} class="input" placeholder="you@gmail.com" />
					</div>
					<div>
						<label class="label" for="smtp-pass">Password</label>
						<input id="smtp-pass" type="password" bind:value={password} class="input" placeholder="Leave blank to keep existing" />
					</div>
				</div>

				<div class="grid grid-cols-2 gap-4">
					<div>
						<label class="label" for="smtp-from">From Email</label>
						<input id="smtp-from" type="email" bind:value={fromEmail} class="input" placeholder="noreply@myapp.com" />
					</div>
					<div>
						<label class="label" for="smtp-name">From Name</label>
						<input id="smtp-name" type="text" bind:value={fromName} class="input" placeholder="My App" />
					</div>
				</div>

				<label class="flex items-center gap-3 cursor-pointer">
					<input type="checkbox" bind:checked={useTls} class="w-4 h-4 accent-coco-500" />
					<span class="text-sm text-gray-300">Use TLS/STARTTLS</span>
				</label>

				<div class="flex gap-2 pt-2">
					<button type="submit" class="btn btn-primary" disabled={saving}>
						{saving ? 'Saving…' : 'Save'}
					</button>
					<button
						type="button"
						class="btn btn-secondary"
						disabled={testing}
						on:click={testSmtp}
					>
						{testing ? 'Testing…' : 'Test Connection'}
					</button>
				</div>
			</form>
		</div>
	{/if}
</div>
