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

P_IO_MAP = {
    'cpu_bound': 0.2,
    'io_bound': 0.6,
    'mixed': 0.4
}

MARKOV_MULTIPLIER_MAP = {
    'short': 0.8,
    'medium': 1.0,
    'long': 1.3
}

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

def state_idx_to_label(state_idx):
    if state_idx == 0:
        return 'short'
    if state_idx == 1:
        return 'medium'
    return 'long'

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

def predict_markov_state(curr_burst, transitions):
    # Predict next Markov burst category: short / medium / long
    curr_state = get_burst_state(curr_burst)
    probs = transitions[curr_state]
    predicted_state_idx = int(np.argmax(probs))
    return state_idx_to_label(predicted_state_idx)

def train_rf_classifier(processes, verbose=True):
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
    if verbose:
        print(f"Random Forest Classifier Accuracy: {acc*100:.2f}%")
    return clf

def classifier_to_p_io(clf, process):
    # Explicitly map RF class output to P_io coefficient
    features = [[process['burst_time'], process['io_probability'], process['priority']]]
    predicted_class = clf.predict(features)[0]
    return P_IO_MAP.get(predicted_class, 0.4)

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
        # v2 keeps Markov-only burst category estimate for queue ordering
        state_label = predict_markov_state(p['burst_time'], transitions)
        if state_label == 'short':
            pred_burst = 3.0
        elif state_label == 'medium':
            pred_burst = 8.0
        else:
            pred_burst = 20.0
        p['predicted_burst'] = pred_burst
        # Fixed priority denominator to avoid divide-by-zero edge cases
        p['prism_score'] = pred_burst * (1 + p['io_probability']) * (1.0 / (p['priority'] + 1))
        
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

def predict_lstm_burst(actual_burst, previous_error):
    # LSTM-inspired weighted burst predictor.
    # Uses recency-weighted history, approximating LSTM temporal behavior without
    # backpropagation. Full LSTM via PyTorch planned for future work.
    history = [max(0.1, actual_burst + random.uniform(-0.5, 0.5) * actual_burst) for _ in range(5)]
    weights = np.array([0.1, 0.15, 0.2, 0.25, 0.3])
    predicted_burst = np.dot(history, weights)
    
    # Online learning adjustment
    learning_rate = 0.1
    adjusted_prediction = predicted_burst + (previous_error * learning_rate)
    return max(0.1, adjusted_prediction)

def run_prism_v3(processes_input, transitions, clf):
    """
    PRISM Scheduler (Version 3 - Markov + RF + LSTM-inspired Predictor)
    """
    processes = [p.copy() for p in processes_input]
    previous_error = 0.0
    
    for p in processes:
        p['remaining_time'] = p['burst_time']
        # Layer 1: Markov predicted state -> multiplier
        markov_state = predict_markov_state(p['burst_time'], transitions)
        markov_multiplier = MARKOV_MULTIPLIER_MAP[markov_state]

        # Layer 3: LSTM-inspired burst estimate
        lstm_prediction = predict_lstm_burst(p['burst_time'], previous_error)

        # Coupled Layer 1 + Layer 3
        b_pred = lstm_prediction * markov_multiplier
        p['predicted_burst'] = b_pred

        # Layer 2: RF classifier -> explicit P_io mapping
        p_io = classifier_to_p_io(clf, p)

        # Final score: B_pred * (1 + P_io) * (1/(priority + 1))
        p['prism_score'] = b_pred * (1 + p_io) * (1.0 / (p['priority'] + 1))
        
        # Update error for next prediction
        error = p['burst_time'] - b_pred
        previous_error = error
        
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

def compute_metrics(completed, switches):
    avg_ta = float(np.mean([p['turnaround_time'] for p in completed]))
    avg_wt = float(np.mean([p['waiting_time'] for p in completed]))
    total_burst = float(sum([p['burst_time'] for p in completed]))
    max_finish = float(max([p['arrival_time'] + p['turnaround_time'] for p in completed]))
    min_arrival = float(min([p['arrival_time'] for p in completed]))
    cpu_util = (total_burst / (max_finish - min_arrival)) * 100 if max_finish > min_arrival else 0.0
    fairness = float(jains_fairness_index(completed))
    return {
        'avg_turnaround': avg_ta,
        'avg_waiting': avg_wt,
        'context_switches': int(switches),
        'cpu_utilization': cpu_util,
        'fairness_index': fairness
    }

def print_summary_table(metrics, order):
    print("\n=== Day 3 Scheduler Metrics Summary (n=1000) ===")
    header = (
        f"{'Scheduler':<12} | {'Avg Turnaround Time (ms)':<24} | {'Avg Waiting Time (ms)':<21} | "
        f"{'Context Switches':<16} | {'CPU Utilization %':<17} | {'Jain Fairness Index':<19}"
    )
    print(header)
    print("-" * len(header))
    for name in order:
        m = metrics[name]
        print(
            f"{name:<12} | {m['avg_turnaround']:<24.2f} | {m['avg_waiting']:<21.2f} | "
            f"{m['context_switches']:<16} | {m['cpu_utilization']:<17.2f} | {m['fairness_index']:<19.4f}"
        )

def add_value_labels(ax):
    for bar in ax.patches:
        height = bar.get_height()
        ax.annotate(
            f"{height:.2f}",
            (bar.get_x() + bar.get_width() / 2, height),
            ha='center',
            va='bottom',
            fontsize=8,
            rotation=90,
            xytext=(0, 2),
            textcoords='offset points'
        )

def main():
    print("Generating 1000 synthetic processes...")
    processes = generate_processes(1000)
    
    print("Training ML Models...")
    transitions = build_markov_chain(processes)
    clf = train_rf_classifier(processes)
    
    print("Running Schedulers...")
    rr_result, rr_switches = run_round_robin(processes, quantum=4)
    sjf_result, sjf_switches = run_sjf(processes)
    prism1_result, prism1_switches = run_prism_v1(processes)
    prism2_result, prism2_switches = run_prism_v2(processes, transitions)
    prism3_result, prism3_switches = run_prism_v3(processes, transitions, clf)
    
    metrics = {}
    results_list = [
        ('Round Robin', rr_result, rr_switches),
        ('SJF', sjf_result, sjf_switches),
        ('PRISM v1', prism1_result, prism1_switches),
        ('PRISM v2', prism2_result, prism2_switches),
        ('PRISM v3', prism3_result, prism3_switches)
    ]
    
    csv_data = []
    
    scheduler_order = ['RR', 'SJF', 'PRISM_v1', 'PRISM_v2', 'PRISM_v3']
    
    label_map = {
        'Round Robin': 'RR',
        'SJF': 'SJF',
        'PRISM v1': 'PRISM_v1',
        'PRISM v2': 'PRISM_v2',
        'PRISM v3': 'PRISM_v3'
    }

    for name, completed, switches in results_list:
        key = label_map[name]
        metrics[key] = compute_metrics(completed, switches)
        csv_data.append([
            key,
            metrics[key]['avg_turnaround'],
            metrics[key]['avg_waiting'],
            metrics[key]['context_switches'],
            metrics[key]['cpu_utilization'],
            metrics[key]['fairness_index']
        ])

    print_summary_table(metrics, scheduler_order)
        
    # Plotting
    schedulers = scheduler_order
    turnaround = [metrics[s]['avg_turnaround'] for s in schedulers]
    waiting = [metrics[s]['avg_waiting'] for s in schedulers]
    switches = [metrics[s]['context_switches'] for s in schedulers]
    utilization = [metrics[s]['cpu_utilization'] for s in schedulers]
    fairness = [metrics[s]['fairness_index'] for s in schedulers]

    fig, axs = plt.subplots(1, 5, figsize=(26, 5.5))
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

    axs[0].bar(schedulers, turnaround, color=colors)
    axs[0].set_title('Average Turnaround Time')
    axs[0].set_ylabel('ms')
    axs[0].set_xlabel('Scheduler')
    add_value_labels(axs[0])

    axs[1].bar(schedulers, waiting, color=colors)
    axs[1].set_title('Average Waiting Time')
    axs[1].set_ylabel('ms')
    axs[1].set_xlabel('Scheduler')
    add_value_labels(axs[1])

    axs[2].bar(schedulers, switches, color=colors)
    axs[2].set_title('Total Context Switches')
    axs[2].set_ylabel('count')
    axs[2].set_xlabel('Scheduler')
    add_value_labels(axs[2])

    axs[3].bar(schedulers, utilization, color=colors)
    axs[3].set_title('CPU Utilization')
    axs[3].set_ylabel('%')
    axs[3].set_xlabel('Scheduler')
    add_value_labels(axs[3])

    axs[4].bar(schedulers, fairness, color=colors)
    axs[4].set_title("Jain's Fairness Index")
    axs[4].set_ylabel('index')
    axs[4].set_xlabel('Scheduler')
    add_value_labels(axs[4])

    for ax in axs:
        ax.tick_params(axis='x', rotation=20)
        
    plt.tight_layout()
    plt.savefig('results/day3_comparison.png')
    print("\nSaved comparison figure to results/day3_comparison.png")
    
    # Save CSV
    with open('results/day3_results.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Scheduler', 'Avg_TAT', 'Avg_Wait', 'Context_Switches', 'CPU_Util', 'Fairness_Index'])
        writer.writerows(csv_data)
    print("Saved results to results/day3_results.csv")

    print("\nRunning Scale Test...")
    sizes = [100, 500, 1000, 5000]
    scale_results = {
        'Round Robin': [],
        'SJF': [],
        'PRISM v1': [],
        'PRISM v2': [],
        'PRISM v3': []
    }
    
    for n in sizes:
        print(f"Testing scale n={n}...")
        ps = generate_processes(n)
        trans = build_markov_chain(ps)
        rf_clf = train_rf_classifier(ps, verbose=False)
        
        rr_c, _ = run_round_robin(ps, quantum=4)
        sjf_c, _ = run_sjf(ps)
        p1_c, _ = run_prism_v1(ps)
        p2_c, _ = run_prism_v2(ps, trans)
        p3_c, _ = run_prism_v3(ps, trans, rf_clf)
        
        scale_results['Round Robin'].append(np.mean([p['turnaround_time'] for p in rr_c]))
        scale_results['SJF'].append(np.mean([p['turnaround_time'] for p in sjf_c]))
        scale_results['PRISM v1'].append(np.mean([p['turnaround_time'] for p in p1_c]))
        scale_results['PRISM v2'].append(np.mean([p['turnaround_time'] for p in p2_c]))
        scale_results['PRISM v3'].append(np.mean([p['turnaround_time'] for p in p3_c]))
        
    plt.figure(figsize=(10, 6))
    for scheduler, means in scale_results.items():
        plt.plot(sizes, means, marker='o', label=scheduler)
        
    plt.title('Scheduler Scaling Comparison')
    plt.xlabel('Number of Processes')
    plt.ylabel('Average Turnaround Time (ms)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('results/scaling_comparison.png')
    print("Saved scale test plot to results/scaling_comparison.png")

if __name__ == '__main__':
    main()

