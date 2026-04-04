import numpy as np
import matplotlib.pyplot as plt
import random
import os
import csv
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

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

def get_burst_state(burst):
    # 3 process states: 'short' (burst < 5), 'medium' (5-15), 'long' (burst > 15)
    if burst < 5: return 0 # short
    elif burst <= 15: return 1 # medium
    else: return 2 # long

def build_markov_chain(processes):
    # Build a 3x3 transition matrix from the generated processes
    transitions = np.zeros((3, 3))
    for i in range(len(processes) - 1):
        curr_state = get_burst_state(processes[i]['burst_time'])
        next_state = get_burst_state(processes[i+1]['burst_time'])
        transitions[curr_state][next_state] += 1
        
    # Normalize rows
    for i in range(3):
        row_sum = np.sum(transitions[i])
        if row_sum > 0:
            transitions[i] = transitions[i] / row_sum
        else:
            transitions[i] = np.array([1/3, 1/3, 1/3])
    return transitions

def predict_markov_burst(curr_burst, transitions):
    # Predict the next state and convert to expected burst time
    curr_state = get_burst_state(curr_burst)
    probs = transitions[curr_state]
    predicted_state = np.argmax(probs)
    if predicted_state == 0: return 3.0
    elif predicted_state == 1: return 8.0
    else: return 20.0

def train_rf_classifier(processes):
    # Features: burst_time, io_probability, priority
    # Label: process_type
    X = [[p['burst_time'], p['io_probability'], p['priority']] for p in processes]
    y = [p['process_type'] for p in processes]
    
    # Train on 70% of generated processes, test on 30%
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
    clf = RandomForestClassifier(n_estimators=50, random_state=42)
    clf.fit(X_train, y_train)
    
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Random Forest Classifier Accuracy: {acc*100:.2f}%")
    return clf

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

def run_prism_v2(processes_input, transitions):
    """
    PRISM Scheduler (Version 2 - Markov Predictor + RF)
    """
    processes = [p.copy() for p in processes_input]
    for p in processes:
        p['remaining_time'] = p['burst_time']
        # 1. Use Markov predicted burst time for queue ordering
        pred_burst = predict_markov_burst(p['burst_time'], transitions)
        p['predicted_burst'] = pred_burst
        # 2. Apply scheduling score logic: score = predicted_burst * (1 + io_probability) * (1/priority)
        p['prism_score'] = pred_burst * (1 + p['io_probability']) * (1.0 / p['priority'])
        
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
            
        # 3. Sort queue by score (lowest first)
        ready_queue.sort(key=lambda x: x['prism_score'])
        current = ready_queue.pop(0)
        
        execute_time = current['remaining_time']
        time += execute_time
        current['remaining_time'] -= execute_time
        
        current['turnaround_time'] = time - current['arrival_time']
        current['waiting_time'] = current['turnaround_time'] - current['burst_time']
        completed.append(current)
        context_switches += 1
        
    return completed, context_switches

def jains_fairness_index(completed):
    # Formula: (sum of turnaround)^2 / (n * sum of turnaround^2)
    turnarounds = np.array([p['turnaround_time'] for p in completed])
    n = len(turnarounds)
    if n == 0 or np.sum(turnarounds**2) == 0:
        return 0
    return (np.sum(turnarounds)**2) / (n * np.sum(turnarounds**2))

def main():
    print("Generating 200 synthetic processes...")
    processes = generate_processes(200)
    
    print("Training ML Models...")
    transitions = build_markov_chain(processes)
    clf = train_rf_classifier(processes)
    
    print("Running Schedulers...")
    rr_result, rr_switches = run_round_robin(processes, quantum=4)
    sjf_result, sjf_switches = run_sjf(processes)
    prism1_result, prism1_switches = run_prism_v1(processes)
    prism2_result, prism2_switches = run_prism_v2(processes, transitions)
    
    metrics = {}
    results_list = [
        ('Round Robin', rr_result, rr_switches),
        ('SJF', sjf_result, sjf_switches),
        ('PRISM v1', prism1_result, prism1_switches),
        ('PRISM v2', prism2_result, prism2_switches)
    ]
    
    csv_data = []
    
    print("\n=== Scheduler Metrics Summary ===")
    print(f"{'Scheduler':<15} | {'Avg TA':<10} | {'Avg WT':<10} | {'Switches':<10} | {'CPU Util %':<10} | {'Fairness':<10}")
    print("-" * 85)
    
    for name, completed, switches in results_list:
        avg_ta = np.mean([p['turnaround_time'] for p in completed])
        avg_wt = np.mean([p['waiting_time'] for p in completed])
        total_burst = sum([p['burst_time'] for p in completed])
        max_finish = max([p['arrival_time'] + p['turnaround_time'] for p in completed])
        min_arrival = min([p['arrival_time'] for p in completed])
        cpu_util = (total_burst / (max_finish - min_arrival)) * 100
        fairness = jains_fairness_index(completed)
        
        metrics[name] = {
            'avg_turnaround': avg_ta,
            'avg_waiting': avg_wt,
            'context_switches': switches,
            'cpu_utilization': cpu_util,
            'fairness_index': fairness
        }
        
        print(f"{name:<15} | {avg_ta:<10.2f} | {avg_wt:<10.2f} | {switches:<10} | {cpu_util:<10.2f}% | {fairness:<10.4f}")
        csv_data.append([name, avg_ta, avg_wt, switches, cpu_util, fairness])
        
    # Plotting
    schedulers = list(metrics.keys())
    turnaround = [metrics[s]['avg_turnaround'] for s in schedulers]
    waiting = [metrics[s]['avg_waiting'] for s in schedulers]
    switches = [metrics[s]['context_switches'] for s in schedulers]
    utilization = [metrics[s]['cpu_utilization'] for s in schedulers]
    
    fig, axs = plt.subplots(1, 4, figsize=(20, 5))
    colors = ['blue', 'orange', 'green', 'red']
    
    axs[0].bar(schedulers, turnaround, color=colors)
    axs[0].set_title('Avg Turnaround Time')
    axs[0].set_ylabel('ms')
    
    axs[1].bar(schedulers, waiting, color=colors)
    axs[1].set_title('Avg Waiting Time')
    axs[1].set_ylabel('ms')
    
    axs[2].bar(schedulers, switches, color=colors)
    axs[2].set_title('Total Context Sw.')
    
    axs[3].bar(schedulers, utilization, color=colors)
    axs[3].set_title('CPU Utilization %')
    axs[3].set_ylabel('%')
    
    for ax in axs.flat:
        ax.set_xticks(range(len(schedulers)))
        ax.set_xticklabels(schedulers, rotation=15, ha='right')
        
    plt.tight_layout()
    plt.savefig('results/day2_comparison.png')
    print("\nSaved comparison figure to results/day2_comparison.png")
    
    # Save CSV
    with open('results/day2_results.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Scheduler', 'Avg_Turnaround', 'Avg_Waiting', 'Context_Switches', 'CPU_Utilization', 'Fairness_Index'])
        writer.writerows(csv_data)
    print("Saved results to results/day2_results.csv")

if __name__ == '__main__':
    main()

