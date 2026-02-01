<script lang="ts">
  import { fetchStats, fetchBurndown, fetchAging, fetchVelocity, fetchPriorityTrend, fetchExecutive } from '$lib/api';
  import type { StatsResponse, BurndownResponse, AgingResponse, VelocityResponse, PriorityTrendResponse, ExecutiveResponse } from '$lib/types';
  import { Button } from '$lib/components/ui/button';
  import * as Card from '$lib/components/ui/card';
  import BurndownChart from '$lib/components/BurndownChart.svelte';
  import VelocityChart from '$lib/components/VelocityChart.svelte';
  import PriorityTrendChart from '$lib/components/PriorityTrendChart.svelte';
  import KeyboardShortcuts from '$lib/components/KeyboardShortcuts.svelte';

  let stats: StatsResponse | null = $state(null);
  let burndown: BurndownResponse | null = $state(null);
  let aging: AgingResponse | null = $state(null);
  let velocity: VelocityResponse | null = $state(null);
  let priorityTrend: PriorityTrendResponse | null = $state(null);
  let executive: ExecutiveResponse | null = $state(null);
  let loading = $state(true);
  let error = $state<string | null>(null);

  function getPriorityColor(priority: string): string {
    if (priority.includes('1')) return 'bg-red-500';
    if (priority.includes('2')) return 'bg-orange-500';
    if (priority.includes('3')) return 'bg-yellow-500';
    if (priority.includes('4')) return 'bg-green-500';
    return 'bg-muted';
  }

  function stripDomain(owner: string): string {
    if (!owner) return '-';
    return owner.includes('_') ? owner.split('_')[0] : owner;
  }

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return '-';
    return new Date(dateStr).toISOString().slice(0, 10);
  }

  $effect(() => {
    Promise.all([fetchStats(), fetchBurndown(), fetchAging(), fetchVelocity(), fetchPriorityTrend(), fetchExecutive()])
      .then(([statsData, burndownData, agingData, velocityData, priorityTrendData, executiveData]) => {
        stats = statsData;
        burndown = burndownData;
        aging = agingData;
        velocity = velocityData;
        priorityTrend = priorityTrendData;
        executive = executiveData;
        loading = false;
      })
      .catch((e) => {
        error = e instanceof Error ? e.message : 'Failed to load stats';
        loading = false;
      });
  });
</script>

<svelte:head>
  <title>Dashboard - ALM Defects</title>
</svelte:head>

<div class="container mx-auto px-4 py-8 max-w-6xl">
  <div class="flex justify-between items-center mb-8">
    <h1 class="text-3xl font-bold">ALM Dashboard</h1>
    <Button href="/">View Defects</Button>
  </div>

  {#if loading}
    <div class="text-center py-12 text-muted-foreground">Loading...</div>
  {:else if error}
    <div class="text-center py-12 text-destructive">{error}</div>
  {:else if stats}
    <!-- Summary Cards -->
    <div class="grid grid-cols-5 gap-4 mb-8">
      {#if executive}
        <a href="/?status=blocked">
          <Card.Root class="hover:bg-muted/50 transition-colors cursor-pointer">
            <Card.Content class="pt-6">
              <div class="text-center">
                <div class="text-4xl font-bold text-red-500">{executive.blocked_count}</div>
                <div class="text-muted-foreground">Blocked</div>
              </div>
            </Card.Content>
          </Card.Root>
        </a>
      {/if}
      <Card.Root>
        <Card.Content class="pt-6">
          <div class="text-center">
            <div class="text-4xl font-bold text-orange-500">{stats.open_count}</div>
            <div class="text-muted-foreground">Active</div>
          </div>
        </Card.Content>
      </Card.Root>
      {#if executive}
        <a href="/?owner=convergint&status=!terminal">
          <Card.Root class="hover:bg-muted/50 transition-colors cursor-pointer">
            <Card.Content class="pt-6">
              <div class="text-center">
                <div class="text-4xl font-bold text-blue-500">{executive.ownership['Convergint']?.active || 0}</div>
                <div class="text-muted-foreground">Convergint</div>
              </div>
            </Card.Content>
          </Card.Root>
        </a>
      {/if}
      <Card.Root>
        <Card.Content class="pt-6">
          <div class="text-center">
            <div class="text-4xl font-bold text-green-500">{stats.closed_count}</div>
            <div class="text-muted-foreground">Resolved</div>
          </div>
        </Card.Content>
      </Card.Root>
      <Card.Root>
        <Card.Content class="pt-6">
          <div class="text-center">
            <div class="text-4xl font-bold">{stats.total}</div>
            <div class="text-muted-foreground">Total</div>
          </div>
        </Card.Content>
      </Card.Root>
    </div>

    <!-- Ownership Split & Action Items -->
    {#if executive}
      <div class="grid grid-cols-2 gap-4 mb-8">
        <!-- Ownership Split -->
        <Card.Root>
          <Card.Header>
            <Card.Title>Ownership Split</Card.Title>
            <p class="text-sm text-muted-foreground">Active defects by responsible party</p>
          </Card.Header>
          <Card.Content>
            <div class="space-y-4">
              {#each Object.entries(executive.ownership) as [party, data]}
                <div class="flex items-center justify-between p-3 bg-muted rounded-lg">
                  <div>
                    <div class="font-medium">{party}</div>
                    <div class="text-sm text-muted-foreground">
                      {data.p1} P1 / {data.p2} P2 critical
                    </div>
                  </div>
                  <div class="text-3xl font-bold">{data.active}</div>
                </div>
              {/each}
            </div>
          </Card.Content>
        </Card.Root>

        <!-- Status Pipeline -->
        <Card.Root>
          <Card.Header>
            <Card.Title>Status Pipeline</Card.Title>
            <p class="text-sm text-muted-foreground">Where defects are in the workflow</p>
          </Card.Header>
          <Card.Content>
            <div class="space-y-2">
              {#each executive.pipeline as item}
                <div class="flex items-center justify-between text-sm">
                  <span class={item.status.toLowerCase() === 'blocked' ? 'text-red-500 font-medium' : ''}>{item.status}</span>
                  <div class="flex items-center gap-4">
                    <span class="text-muted-foreground">{item.avg_days_stale}d avg</span>
                    <span class="font-mono font-medium w-8 text-right">{item.count}</span>
                  </div>
                </div>
              {/each}
            </div>
          </Card.Content>
        </Card.Root>
      </div>

      <!-- Attention Required Section -->
      {#if executive.high_priority_stale.length > 0 || executive.stale_convergint.length > 0 || executive.blocked.length > 0}
        <Card.Root class="mb-8 border-red-500/50">
          <Card.Header>
            <Card.Title class="text-red-500">Attention Required</Card.Title>
            <p class="text-sm text-muted-foreground">Issues that may need escalation or follow-up</p>
          </Card.Header>
          <Card.Content>
            <div class="space-y-6">
              <!-- High Priority Not Started -->
              {#if executive.high_priority_stale.length > 0}
                <div>
                  <h4 class="font-medium mb-2 flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-red-500"></span>
                    P1/P2 in "New" for 2+ days
                  </h4>
                  <div class="space-y-1">
                    {#each executive.high_priority_stale as defect}
                      <div class="flex items-center justify-between text-sm">
                        <a href="/defects/{defect.id}" class="text-primary hover:underline truncate max-w-[50%]">
                          #{defect.id}: {defect.name}
                        </a>
                        <div class="flex items-center gap-3">
                          <span class="text-muted-foreground">{defect.owner || 'Unassigned'}</span>
                          <span class="px-2 py-0.5 rounded text-xs {getPriorityColor(defect.priority)} text-white">{defect.priority}</span>
                          <span class="text-muted-foreground">{defect.age_days}d</span>
                        </div>
                      </div>
                    {/each}
                  </div>
                </div>
              {/if}

              <!-- Stale Convergint Defects -->
              {#if executive.stale_convergint.length > 0}
                <div>
                  <h4 class="font-medium mb-2 flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-orange-500"></span>
                    Convergint-owned with no update in 7+ days
                  </h4>
                  <div class="space-y-1">
                    {#each executive.stale_convergint as defect}
                      <div class="flex items-center justify-between text-sm">
                        <a href="/defects/{defect.id}" class="text-primary hover:underline truncate max-w-[40%]">
                          #{defect.id}: {defect.name}
                        </a>
                        <div class="flex items-center gap-3">
                          <span class="text-muted-foreground">{defect.owner}</span>
                          <span class="text-xs text-muted-foreground">{defect.status}</span>
                          <span class="px-2 py-0.5 rounded text-xs {getPriorityColor(defect.priority || '')} text-white">{defect.priority}</span>
                          <span class="text-red-500 font-medium">{defect.days_stale}d stale</span>
                        </div>
                      </div>
                    {/each}
                  </div>
                </div>
              {/if}

              <!-- Blocked Defects -->
              {#if executive.blocked.length > 0}
                <div>
                  <h4 class="font-medium mb-2 flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-yellow-500"></span>
                    Blocked defects
                  </h4>
                  <div class="space-y-1">
                    {#each executive.blocked.slice(0, 5) as defect}
                      <div class="flex items-center justify-between text-sm">
                        <a href="/defects/{defect.id}" class="text-primary hover:underline truncate max-w-[50%]">
                          #{defect.id}: {defect.name}
                        </a>
                        <div class="flex items-center gap-3">
                          <span class="text-muted-foreground">{defect.owner || 'Unassigned'}</span>
                          <span class="px-2 py-0.5 rounded text-xs {getPriorityColor(defect.priority || '')} text-white">{defect.priority}</span>
                          <span class="text-muted-foreground">{defect.days_stale}d stale</span>
                        </div>
                      </div>
                    {/each}
                    {#if executive.blocked.length > 5}
                      <a href="/?status=blocked" class="text-sm text-primary hover:underline">
                        View all {executive.blocked_count} blocked defects
                      </a>
                    {/if}
                  </div>
                </div>
              {/if}
            </div>
          </Card.Content>
        </Card.Root>
      {/if}

      <!-- Convergint Owner Scorecard -->
      {#if executive.convergint_owners.length > 0}
        <Card.Root class="mb-8">
          <Card.Header>
            <Card.Title>Convergint Owner Scorecard</Card.Title>
            <p class="text-sm text-muted-foreground">Active defects owned by Convergint team members</p>
          </Card.Header>
          <Card.Content>
            <div class="overflow-x-auto">
              <table class="w-full text-sm">
                <thead>
                  <tr class="border-b">
                    <th class="text-left py-2">Owner</th>
                    <th class="text-right py-2">Active</th>
                    <th class="text-right py-2">P1/P2</th>
                    <th class="text-right py-2">Avg Age</th>
                    <th class="text-right py-2">Max Stale</th>
                  </tr>
                </thead>
                <tbody>
                  {#each executive.convergint_owners as owner}
                    <tr class="border-b">
                      <td class="py-2">
                        <a href="/?owner={owner.owner_raw}&status=!terminal" class="text-primary hover:underline">
                          {owner.owner}
                        </a>
                      </td>
                      <td class="text-right py-2 font-mono">{owner.active}</td>
                      <td class="text-right py-2 font-mono {owner.high_priority > 0 ? 'text-red-500 font-medium' : ''}">{owner.high_priority}</td>
                      <td class="text-right py-2 font-mono text-muted-foreground">{owner.avg_age}d</td>
                      <td class="text-right py-2 font-mono {owner.max_days_stale >= 7 ? 'text-orange-500' : 'text-muted-foreground'}">{owner.max_days_stale}d</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </Card.Content>
        </Card.Root>
      {/if}
    {/if}

    <!-- Burndown Chart -->
    {#if burndown && burndown.dates.length > 0}
      <Card.Root class="mb-8">
        <Card.Header>
          <Card.Title>Defect Burndown</Card.Title>
          {#if burndown.prediction}
            <p class="text-sm text-muted-foreground">
              Recent trend: {burndown.prediction.daily_close_rate} closed/day, {burndown.prediction.daily_open_rate} opened/day
              (net burn: {burndown.prediction.net_burn_rate}/day)
            </p>
          {/if}
        </Card.Header>
        <Card.Content>
          <BurndownChart data={burndown} />
        </Card.Content>
      </Card.Root>
    {/if}

    <!-- Velocity and Priority Trend Charts -->
    <div class="grid grid-cols-2 gap-4 mb-8">
      {#if velocity && velocity.weeks.length > 0}
        <Card.Root>
          <Card.Header>
            <Card.Title>Weekly Velocity</Card.Title>
            <p class="text-sm text-muted-foreground">
              Avg: {velocity.avg_opened_per_week} opened, {velocity.avg_resolved_per_week} resolved/week
              (net: {velocity.avg_net_per_week > 0 ? '+' : ''}{velocity.avg_net_per_week}/week)
            </p>
          </Card.Header>
          <Card.Content>
            <VelocityChart data={velocity} />
          </Card.Content>
        </Card.Root>
      {/if}

      {#if priorityTrend && priorityTrend.weeks.length > 0}
        <Card.Root>
          <Card.Header>
            <Card.Title>Priority Trend</Card.Title>
            <p class="text-sm text-muted-foreground">Open defects by priority over time</p>
          </Card.Header>
          <Card.Content>
            <PriorityTrendChart data={priorityTrend} />
          </Card.Content>
        </Card.Root>
      {/if}
    </div>

    <!-- Aging Analysis -->
    {#if aging}
      <Card.Root class="mb-8">
        <Card.Header>
          <Card.Title>Aging Analysis</Card.Title>
          <p class="text-sm text-muted-foreground">How long open defects have been waiting</p>
        </Card.Header>
        <Card.Content>
          <div class="grid grid-cols-4 gap-4 mb-6">
            {#each Object.entries(aging.buckets) as [bucket, count]}
              <div class="text-center p-4 bg-muted rounded-lg">
                <div class="text-2xl font-bold">{count}</div>
                <div class="text-sm text-muted-foreground">{bucket}</div>
              </div>
            {/each}
          </div>

          {#if aging.by_priority.length > 0}
            <div class="mb-4">
              <h4 class="font-medium mb-2">By Priority</h4>
              <div class="overflow-x-auto">
                <table class="w-full text-sm">
                  <thead>
                    <tr class="border-b">
                      <th class="text-left py-2">Priority</th>
                      <th class="text-right py-2">0-7 days</th>
                      <th class="text-right py-2">8-30 days</th>
                      <th class="text-right py-2">31-90 days</th>
                      <th class="text-right py-2">90+ days</th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each aging.by_priority as row}
                      <tr class="border-b">
                        <td class="py-2 flex items-center gap-2">
                          <span class="w-3 h-3 rounded-full {getPriorityColor(row.priority)}"></span>
                          {row.priority}
                        </td>
                        <td class="text-right py-2">{row['0-7 days']}</td>
                        <td class="text-right py-2">{row['8-30 days']}</td>
                        <td class="text-right py-2">{row['31-90 days']}</td>
                        <td class="text-right py-2">{row['90+ days']}</td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            </div>
          {/if}

          {#if aging.oldest.length > 0}
            <div>
              <h4 class="font-medium mb-2">Oldest Open Defects</h4>
              <div class="space-y-2">
                {#each aging.oldest as defect}
                  <div class="flex items-center justify-between text-sm">
                    <a href="/defects/{defect.id}" class="text-primary hover:underline truncate max-w-[60%]">
                      #{defect.id}: {defect.name}
                    </a>
                    <div class="flex items-center gap-4">
                      <span class="px-2 py-0.5 rounded text-xs {getPriorityColor(defect.priority)} text-white">{defect.priority}</span>
                      <span class="text-muted-foreground">{defect.age_days} days</span>
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
        </Card.Content>
      </Card.Root>
    {/if}

    <!-- Priority and Owners -->
    <div class="grid grid-cols-2 gap-4 mb-8">
      <Card.Root>
        <Card.Header>
          <Card.Title>Open by Priority</Card.Title>
        </Card.Header>
        <Card.Content>
          <div class="space-y-3">
            {#each stats.by_priority as item}
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="w-3 h-3 rounded-full {getPriorityColor(item.name)}"></span>
                  <span>{item.name || '(none)'}</span>
                </div>
                <span class="font-mono text-muted-foreground">{item.count}</span>
              </div>
            {/each}
          </div>
        </Card.Content>
      </Card.Root>

      <Card.Root>
        <Card.Header>
          <Card.Title>Top Owners (Open)</Card.Title>
        </Card.Header>
        <Card.Content>
          <div class="space-y-3">
            {#each stats.by_owner as item, i}
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="text-muted-foreground w-4">{i + 1}.</span>
                  <span>{stripDomain(item.name)}</span>
                </div>
                <span class="font-mono text-muted-foreground">{item.count}</span>
              </div>
            {/each}
          </div>
        </Card.Content>
      </Card.Root>
    </div>

    <!-- Scenarios and Close Time -->
    <div class="grid grid-cols-2 gap-4 mb-8">
      <Card.Root>
        <Card.Header>
          <Card.Title>Top Scenarios (Open)</Card.Title>
        </Card.Header>
        <Card.Content>
          {#if stats.by_scenario.length > 0}
            <div class="space-y-3">
              {#each stats.by_scenario as item}
                <div class="flex items-center justify-between">
                  <a href="/?scenario={item.name}&status=open" class="text-primary hover:underline">
                    {item.name}
                  </a>
                  <span class="font-mono text-muted-foreground">{item.count} defects</span>
                </div>
              {/each}
            </div>
          {:else}
            <div class="text-muted-foreground">No scenario data</div>
          {/if}
        </Card.Content>
      </Card.Root>

      <Card.Root>
        <Card.Header>
          <Card.Title>Time to Close</Card.Title>
        </Card.Header>
        <Card.Content>
          {#if stats.close_time}
            <div class="space-y-3">
              <div class="flex justify-between">
                <span>Median</span>
                <span class="font-mono text-muted-foreground">{stats.close_time.p50} days</span>
              </div>
              <div class="flex justify-between">
                <span>75th Percentile</span>
                <span class="font-mono text-muted-foreground">{stats.close_time.p75} days</span>
              </div>
              <div class="flex justify-between">
                <span>Average</span>
                <span class="font-mono text-muted-foreground">{stats.close_time.avg} days</span>
              </div>
            </div>
          {:else}
            <div class="text-muted-foreground">No close time data</div>
          {/if}
        </Card.Content>
      </Card.Root>
    </div>

    <!-- Workstreams and Types -->
    <div class="grid grid-cols-2 gap-4 mb-8">
      <Card.Root>
        <Card.Header>
          <Card.Title>Top Workstreams (Open)</Card.Title>
        </Card.Header>
        <Card.Content>
          <div class="space-y-3">
            {#each stats.by_workstream as item}
              <div class="flex items-center justify-between">
                <a href="/?workstream={encodeURIComponent(item.name)}" class="text-primary hover:underline">{item.name}</a>
                <span class="font-mono text-muted-foreground">{item.count}</span>
              </div>
            {/each}
          </div>
        </Card.Content>
      </Card.Root>

      <Card.Root>
        <Card.Header>
          <Card.Title>Top Defect Types (Open)</Card.Title>
        </Card.Header>
        <Card.Content>
          <div class="space-y-3">
            {#each stats.by_type as item}
              <div class="flex items-center justify-between">
                <a href="/?defect_type={encodeURIComponent(item.name)}" class="text-primary hover:underline">{item.name}</a>
                <span class="font-mono text-muted-foreground">{item.count}</span>
              </div>
            {/each}
          </div>
        </Card.Content>
      </Card.Root>
    </div>

    <!-- Oldest Open Defect -->
    {#if stats.oldest_open}
      <Card.Root>
        <Card.Header>
          <Card.Title>Oldest Open Defect</Card.Title>
        </Card.Header>
        <Card.Content>
          <div class="flex items-center justify-between">
            <a href="/defects/{stats.oldest_open.id}" class="text-primary hover:underline">
              #{stats.oldest_open.id}: {stats.oldest_open.name}
            </a>
            <span class="text-muted-foreground">{formatDate(stats.oldest_open.created)}</span>
          </div>
        </Card.Content>
      </Card.Root>
    {/if}
  {/if}
</div>

<KeyboardShortcuts />
