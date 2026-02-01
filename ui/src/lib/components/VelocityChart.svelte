<script lang="ts">
  import { onMount } from 'svelte';
  import type { VelocityResponse } from '$lib/types';
  import {
    Chart,
    BarController,
    BarElement,
    LineController,
    LineElement,
    PointElement,
    LinearScale,
    CategoryScale,
    Legend,
    Tooltip,
  } from 'chart.js';

  Chart.register(
    BarController,
    BarElement,
    LineController,
    LineElement,
    PointElement,
    LinearScale,
    CategoryScale,
    Legend,
    Tooltip
  );

  interface Props {
    data: VelocityResponse;
  }

  let { data }: Props = $props();
  let canvas: HTMLCanvasElement;
  let chart: Chart | null = null;

  function createChart() {
    if (chart) {
      chart.destroy();
    }

    if (!data.weeks.length) return;

    // Format week labels (W05 -> just week number)
    const labels = data.weeks.map(w => w.week.split('-')[1] || w.week);

    chart = new Chart(canvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'Opened',
            data: data.weeks.map(w => w.opened),
            backgroundColor: 'rgba(239, 68, 68, 0.7)',
            borderColor: 'rgb(239, 68, 68)',
            borderWidth: 1,
          },
          {
            label: 'Resolved',
            data: data.weeks.map(w => w.resolved),
            backgroundColor: 'rgba(34, 197, 94, 0.7)',
            borderColor: 'rgb(34, 197, 94)',
            borderWidth: 1,
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
