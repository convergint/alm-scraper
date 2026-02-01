<script lang="ts">
  import { onMount } from 'svelte';
  import type { BurndownResponse } from '$lib/types';
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

  // Register Chart.js components
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
    data: BurndownResponse;
  }

  let { data }: Props = $props();
  let canvas: HTMLCanvasElement;
  let chart: Chart | null = null;

  function createChart() {
    if (chart) {
      chart.destroy();
    }

    if (!data.dates.length) return;

    // Combine historical and prediction data for the open count line
    const allDates = [...data.dates];
    const allOpenCount = [...data.open_count];

    // Prediction data (separate dataset for dashed line)
    let predictionDates: string[] = [];
    let predictionOpen: (number | null)[] = [];

    if (data.prediction) {
      predictionDates = data.prediction.dates;
      // Start prediction from the last actual value
      predictionOpen = [data.open_count[data.open_count.length - 1], ...data.prediction.open_count];
      // Add the connection point date
      predictionDates = [data.dates[data.dates.length - 1], ...predictionDates];
    }

    // Sample data if too many points (keep every nth point for display)
    const maxPoints = 120;
    let sampleRate = 1;
    if (allDates.length > maxPoints) {
      sampleRate = Math.ceil(allDates.length / maxPoints);
    }

    const sampledDates = allDates.filter((_, i) => i % sampleRate === 0 || i === allDates.length - 1);
    const sampledOpened = data.cumulative_opened.filter((_, i) => i % sampleRate === 0 || i === data.cumulative_opened.length - 1);
    const sampledClosed = data.cumulative_closed.filter((_, i) => i % sampleRate === 0 || i === data.cumulative_closed.length - 1);
    const sampledOpen = allOpenCount.filter((_, i) => i % sampleRate === 0 || i === allOpenCount.length - 1);

    // Sample prediction too
    let sampledPredDates = predictionDates;
    let sampledPredOpen = predictionOpen;
    if (predictionDates.length > 30) {
      const predSampleRate = Math.ceil(predictionDates.length / 30);
      sampledPredDates = predictionDates.filter((_, i) => i % predSampleRate === 0 || i === predictionDates.length - 1);
      sampledPredOpen = predictionOpen.filter((_, i) => i % predSampleRate === 0 || i === predictionOpen.length - 1);
    }

    // Format dates for display (MM/DD)
    const formatDate = (d: string) => {
      const [, month, day] = d.split('-');
      return `${month}/${day}`;
    };

    chart = new Chart(canvas, {
      type: 'line',
      data: {
        labels: [...sampledDates.map(formatDate), ...sampledPredDates.slice(1).map(formatDate)],
        datasets: [
          {
            label: 'Cumulative Opened',
            data: [...sampledOpened, ...Array(sampledPredDates.length - 1).fill(null)],
            borderColor: 'rgb(59, 130, 246)',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            tension: 0.1,
            pointRadius: 0,
            borderWidth: 2,
          },
          {
            label: 'Cumulative Closed',
            data: [...sampledClosed, ...Array(sampledPredDates.length - 1).fill(null)],
            borderColor: 'rgb(34, 197, 94)',
            backgroundColor: 'rgba(34, 197, 94, 0.1)',
            tension: 0.1,
            pointRadius: 0,
            borderWidth: 2,
          },
          {
            label: 'Open Count',
            data: [...sampledOpen, ...Array(sampledPredDates.length - 1).fill(null)],
            borderColor: 'rgb(249, 115, 22)',
            backgroundColor: 'rgba(249, 115, 22, 0.2)',
            fill: true,
            tension: 0.1,
            pointRadius: 0,
            borderWidth: 2,
          },
          ...(data.prediction ? [{
            label: 'Projected',
            data: [...Array(sampledDates.length - 1).fill(null), ...sampledPredOpen],
            borderColor: 'rgb(249, 115, 22)',
            borderDash: [5, 5],
            tension: 0.1,
            pointRadius: 0,
            borderWidth: 2,
          }] : []),
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
              maxRotation: 45,
              minRotation: 45,
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
      if (chart) {
        chart.destroy();
      }
    };
  });

  $effect(() => {
    if (data && canvas) {
      createChart();
    }
  });
</script>

<div class="w-full h-80">
  <canvas bind:this={canvas}></canvas>
</div>
