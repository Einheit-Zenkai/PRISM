import numpy as np
import matplotlib.pyplot as plt
import random
import os

# Create results folder if it doesn't exist
if not os.path.exists('results'):
    os.makedirs('results')

def generate_processes(num_processes=200):
    """
    Generates synthetic processes for the Day 1 simulation.
    """
    processes = []
    types = ['cpu_bound', 'io_bound', 'mixed']
    
    for i in range(num_processes):
        p = {
            'pid': i + 1,
            'arrival_time': random.randint(0, 50),
            'burst_time': max(1.0, random.expovariate(1.0 / 8.0)), # mean=8
            'io_probability': random.uniform(0.1, 0.8),
            'priority': random.randint(1, 5),
            'process_type': random.choice(types),
            'remaining_time': 0.0 # to be populated in scheduler
        }
        processes.append(p)
        
    # Sort primarily by arrival time
    processes.sort(key=lambda x: x['arrival_time'])
    return processes

def run_round_robin(processes_input, quantum=4):
    """
    Round Robin Scheduler
    """
    processes = [p.copy() for p in processes_input]
    for p in processes:
        p['remaining_time'] = p['burst_time']
        
    time = 0
    ready_queue = []
    idx = 0
    n = len(processes)
    completed = []
    context_switches = 0
    
    while len(completed) < n:
        # Add processes that have arrived up to 'time'
        while idx < n and processes[idx]['arrival_time'] <= time:
            ready_queue.append(processes[idx])
            idx += 1
            
        if not ready_queue:
            time = processes[idx]['arrival_time']
            continue
            
        current = ready_queue.pop(0)
        
        # Calculate time slice
        execute_time = min(quantum, current['remaining_time'])
        time += execute_time
        current['remaining_time'] -= execute_time
        
        # Check arrival during execution and add them
        while idx < n and processes[idx]['arrival_time'] <= time:
            ready_queue.append(processes[idx])
            idx += 1
            
        if current['remaining_time'] <= 0.0001:
            current['turnaround_time'] = time - current['arrival_time']
            current['waiting_time'] = current['turnaround_time'] - current['burst_time']
            completed.append(current)
        else:
            ready_queue.append(current)
            context_switches += 1
            
    return completed, context_switches

def run_sjf(processes_input):
    """
    Shortest Job First Scheduler (Non-preemptive)
    """
    processes = [p.copy() for p in processes_input]
    for p in processes:
        p['remaining_time'] = p['burst_time']
        
    time = 0
    ready_queue = []
    idx = 0
    n = len(processes)
    completed = []
    context_switches = 0
    
    while len(completed) < n:
        while idx < n and processes[idx]['arrival_time'] <= time:
            ready_queue.append(processes[idx])
            idx += 1
            
        if not ready_queue:
            time = processes[idx]['arrival_time']
            continue
            
        # Select shortest job
        ready_queue.sort(key=lambda x: x['remaining_time'])
        current = ready_queue.pop(0)
        
        execute_time = current['remaining_time']
        time += execute_time
        current['remaining_time'] -= execute_time
        
        current['turnaround_time'] = time - current['arrival_time']
        current['waiting_time'] = current['turnaround_time'] - current['burst_time']
        completed.append(current)
        context_switches += 1
        
    return completed, context_switches

def run_prism_v1(processes_input):
    """
    PRISM Scheduler (Version 1 - ML Placeholder)
    Sorts by predicted burst using moving average + 10% random noise.
    """
    processes = [p.copy() for p in processes_input]
    for p in processes:
        p['remaining_time'] = p['burst_time']
        # PRISM logic - simulated prediction
        noise = random.uniform(-0.1, 0.1) * p['burst_time']
        p['predicted_burst'] = max(0.1, p['burst_time'] + noise)
        
    time = 0
    ready_queue = []
    idx = 0
    n = len(processes)
    completed = []
    context_switches = 0
    
    while len(completed) < n:
        while idx < n and processes[idx]['arrival_time'] <= time:
            ready_queue.append(processes[idx])
            idx += 1
            
        if not ready_queue:
            time = processes[idx]['arrival_time']
            continue
            
        # Select job based on PRISM's predicted burst time
        ready_queue.sort(key=lambda x: x['predicted_burst'])
        current = ready_queue.pop(0)
        
        execute_time = current['remaining_time']
        time += execute_time
        current['remaining_time'] -= execute_time
        
        current['turnaround_time'] = time - current['arrival_time']
        current['waiting_time'] = current['turnaround_time'] - current['burst_time']
        completed.append(current)
        context_switches += 1
        
    return completed, context_switches

def calculate_metrics(completed, context_switches):
    """
    Calculates summary metrics for a scheduler result.
    """
    avg_turnaround = np.mean([p['turnaround_time'] for p in completed])
    avg_waiting = np.mean([p['waiting_time'] for p in completed])
    
    total_burst = sum([p['burst_time'] for p in completed])
    max_finish = max([p['arrival_time'] + p['turnaround_time'] for p in completed])
    min_arrival = min([p['arrival_time'] for p in completed])
    cpu_utilization = (total_burst / (max_finish - min_arrival)) * 100
    
    return {
        'avg_turnaround': avg_turnaround,
        'avg_waiting': avg_waiting,
        'context_switches': context_switches,
        'cpu_utilization': cpu_utilization
    }

def main():
    print("Generating 200 synthetic processes...")
    processes = generate_processes(200)
    
    print("Running Schedulers...")
    rr_result, rr_switches = run_round_robin(processes, quantum=4)
    sjf_result, sjf_switches = run_sjf(processes)
    prism_result, prism_switches = run_prism_v1(processes)
    
    metrics = {
        'Round Robin': calculate_metrics(rr_result, rr_switches),
        'SJF': calculate_metrics(sjf_result, sjf_switches),
        'PRISM v1': calculate_metrics(prism_result, prism_switches)
    }
    
    print("\n=== Scheduler Metrics Summary ===")
    print(f"{'Scheduler':<20} | {'Avg Turnaround':<15} | {'Avg Waiting':<15} | {'Switches':<10} | {'CPU Util %':<10}")
    print("-" * 75)
    for name, m in metrics.items():
        print(f"{name:<20} | {m['avg_turnaround']:<15.2f} | {m['avg_waiting']:<15.2f} | {m['context_switches']:<10} | {m['cpu_utilization']:<10.2f}%")
        
    # Plotting
    schedulers = list(metrics.keys())
    turnaround = [metrics[s]['avg_turnaround'] for s in schedulers]
    waiting = [metrics[s]['avg_waiting'] for s in schedulers]
    switches = [metrics[s]['context_switches'] for s in schedulers]
    utilization = [metrics[s]['cpu_utilization'] for s in schedulers]
    
    fig, axs = plt.subplots(1, 4, figsize=(20, 5))
    
    axs[0].bar(schedulers, turnaround, color=['blue', 'orange', 'green'])
    axs[0].set_title('Avg Turnaround Time')
    axs[0].set_ylabel('ms')
    
    axs[1].bar(schedulers, waiting, color=['blue', 'orange', 'green'])
    axs[1].set_title('Avg Waiting Time')
    axs[1].set_ylabel('ms')
    
    axs[2].bar(schedulers, switches, color=['blue', 'orange', 'green'])
    axs[2].set_title('Total Context Sw. (Preemptions included)')
    
    axs[3].bar(schedulers, utilization, color=['blue', 'orange', 'green'])
    axs[3].set_title('CPU Utilization %')
    axs[3].set_ylabel('%')
    
    # Use set_ticklabels properly for newer matplotlib versions
    for ax in axs.flat:
        ax.set_xticks(range(len(schedulers)))
        ax.set_xticklabels(schedulers, rotation=15, ha='right')
        
    plt.tight_layout()
    plt.savefig('results/day1_comparison.png')
    print("\nSaved comparison figure to results/day1_comparison.png")

if __name__ == '__main__':
    main()
