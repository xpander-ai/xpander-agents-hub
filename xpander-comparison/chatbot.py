import json
import os
import sys
import argparse

import yaml

from with_xpander.run_query import run_company_analysis as with_run_company_analysis
from without_xpander.run_query import run_company_analysis as without_run_company_analysis

from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
from dotenv import load_dotenv
load_dotenv()

GREEN = '\033[92m'
RESET = '\033[0m'


def process_company(company, run_type, model, tools):
    print(f"******* starting company analysis on {company} with run type {run_type} using the model {model} *******")
    try:
        metadata = {}
        if run_type == "without_xpander":
            metadata = without_run_company_analysis(company, model, tools=tools)
        if run_type == "with_xpander":
            metadata = with_run_company_analysis(company, model)
        metadata["company"] = company
        metadata["run_type"] = run_type
        metadata["model"] = model
        return metadata
    except Exception as e:
        print(f"Error occurred for {company}: {str(e)}")
        return None

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Run pip chatbot with or without xpander')
    parser.add_argument('--run-type',
                       choices=['with_xpander', 'without_xpander', 'both'],
                       default='with_xpander',
                       help='Specify whether to run with or without xpander')
    parser.add_argument('--model',
                        choices=['gpt-4o-mini', 'gpt-4o'],
                        default='gpt-4o',
                        help='Specify the model')
    parser.add_argument('--mode',
                    choices=['append', 'override'],
                    default='append',
                    help='Specify whether to append or override existing results')


    args = parser.parse_args()
    run_type = args.run_type
    run_types = ['without_xpander', 'with_xpander'] if run_type == 'both' else [run_type]
    model = args.model
    mode = args.mode

    try:
        with open('without_xpander/tools.json', 'r') as file:
            tools = json.load(file)
    except FileNotFoundError:
        print("Error: tools.json file not found")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in tools.json")
        sys.exit(1)

    results_dir = 'results'
    os.makedirs(results_dir, exist_ok=True)
    results_file = os.path.join(results_dir, 'final_results.yaml')

    aggregated_metadata = init_results(mode, results_file)

    # Get user query from input
    try:
        with open('companies.txt', 'r') as file:
            companies = file.read().splitlines()
    except FileNotFoundError:
        print("Error: companies.txt file not found")
        sys.exit(1)


    # Process companies in batches of 6
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for company in companies:
            for tmp_run_type in run_types:
                future = executor.submit(process_company, company, tmp_run_type, model, tools)
                futures.append(future)

        # Collect results as they complete
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                aggregated_metadata.append(result)

        # Save results after each batch
        with open(results_file, 'w') as outfile:
            yaml.dump(aggregated_metadata, outfile, indent=2)


def init_results(mode, results_file):
    aggregated_metadata = []
    if mode == 'append' and os.path.exists(results_file):
        try:
            with open(results_file, 'r') as infile:
                existing_data = yaml.safe_load(infile) or []
            aggregated_metadata.extend(existing_data)
        except Exception as e:
            print(f"Error reading existing results: {str(e)}")
    return aggregated_metadata


if __name__ == "__main__":
    main()
