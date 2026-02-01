<script lang="ts">
  import { onMount } from 'svelte';
  import type { PriorityTrendResponse } from '$lib/types';
  import {
    Chart,
    LineController,
    LineElement,
    PointElement,
    LinearScale,
    CategoryScale,
    Filler,
    Legend,
    Tooltip,
  } from 'chart.js';

  Chart.register(
    LineController,
    LineElement,
    PointElement,
    LinearScale,
    CategoryScale,
    Filler,
    Legend,
    Tooltip
  );

  interface Props {
    data: PriorityTrendResponse;
  }

  let { data }: Props = $props();
  let canvas: HTMLCanvasElement;
  let chart: Chart | null = null;

  function createChart() {
    if (chart) {
      chart.destroy();
    }

    if (!data.weeks.length) return;

    // Format week labels
    const labels = data.weeks.map(w => {
      const [, month, day] = w.week.split('-');
      return `${month}/${day}`;
    });

    chart = new Chart(canvas, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'P1 Critical',
            data: data.weeks.map(w => w.P1),
            borderColor: 'rgb(239, 68, 68)',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            fill: true,
            tension: 0.3,
            pointRadius: 2,
          },
          {
            label: 'P2 High',
            data: data.weeks.map(w => w.P2),
            borderColor: 'rgb(249, 115, 22)',
            backgroundColor: 'rgba(249, 115, 22, 0.1)',
            fill: true,
            tension: 0.3,
            pointRadius: 2,
          },
          {
            label: 'P3 Medium',
            data: data.weeks.map(w => w.P3),
            borderColor: 'rgb(234, 179, 8)',
            backgroundColor: 'rgba(234, 179, 8, 0.1)',
            fill: true,
            tension: 0.3,
            pointRadius: 2,
          },
          {
            label: 'P4 Low',
            data: data.weeks.map(w => w.P4),
            borderColor: 'rgb(34, 197, 94)',
            backgroundColor: 'rgba(34, 197, 94, 0.1)',
            fill: true,
            tension: 0.3,
            pointRadius: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          intersect: false,
          mode: 'index',
        },
        plugins: {
          legend: {
            position: 'top',
            labels: {
              color: 'rgb(156, 163, 175)',
              usePointStyle: true,
            },
          },
          tooltip: {
            backgroundColor: 'rgb(30, 41, 59)',
            titleColor: 'rgb(226, 232, 240)',
            bodyColor: 'rgb(226, 232, 240)',
          },
        },
        scales: {
          x: {
            ticks: {
              color: 'rgb(156, 163, 175)',
            },
            grid: {
              color: 'rgba(156, 163, 175, 0.1)',
            },
          },
          y: {
            stacked: true,
            beginAtZero: true,
            ticks: {
              color: 'rgb(156, 163, 175)',
            },
            grid: {
              color: 'rgba(156, 163, 175, 0.1)',
            },
          },
        },
      },
    });
  }

  onMount(() => {
    createChart();
    return () => {
      if (chart) chart.destroy();
    };
  });

  $effect(() => {
    if (data && canvas) {
      createChart();
    }
  });
</script>

<div class="w-full h-64">
  <canvas bind:this={canvas}></canvas>
</div>
