"""
Demo Flow Script
Demonstrates the complete Agentic OS workflow:
1. Task submission
2. Status polling
3. Approval request (HITL)
4. Task completion
"""

import httpx
import json
import time
import asyncio
from typing import Dict, Any
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000"
TENANT_ID = "acme"
AUTH_TOKEN = f"Bearer tenant_{TENANT_ID}_v1"

# Colors for console output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{title:^70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.ENDC}\n")


def print_status(message: str, status: str = "INFO"):
    """Print a status message with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    if status == "SUCCESS":
        color = Colors.GREEN
    elif status == "ERROR":
        color = Colors.RED
    elif status == "WARNING":
        color = Colors.YELLOW
    else:
        color = Colors.BLUE
    
    print(f"{Colors.GRAY}[{timestamp}]{Colors.ENDC} {color}[{status}]{Colors.ENDC} {message}")


async def check_health() -> bool:
    """Check if API is healthy"""
    print_section("STEP 1: Health Check")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_BASE_URL}/health",
                timeout=5.0
            )
        
        if response.status_code == 200:
            health = response.json()
            print_status("API is healthy", "SUCCESS")
            print(f"\nComponents Status:")
            for component, status in health.get("components", {}).items():
                status_color = Colors.GREEN if status == "healthy" else Colors.YELLOW
                print(f"  {status_color}• {component}: {status}{Colors.ENDC}")
            return True
        else:
            print_status(f"Health check failed: {response.status_code}", "ERROR")
            return False
    
    except Exception as e:
        print_status(f"Could not connect to API: {str(e)}", "ERROR")
        print_status("Make sure the server is running: python main.py", "WARNING")
        return False


async def submit_task(task_description: str) -> Dict[str, Any]:
    """Submit a task to the Agentic OS"""
    print_section("STEP 2: Submit Task")
    
    print_status(f"Submitting task: '{task_description}'", "INFO")
    print_status(f"Tenant: {TENANT_ID}", "INFO")
    
    payload = {
        "task": task_description,
        "workflow_id": "default",
        "metadata": {
            "source": "demo_flow",
            "priority": "normal"
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/submit",
                json=payload,
                headers={"Authorization": AUTH_TOKEN},
                timeout=10.0
            )
        
        if response.status_code == 200:
            result = response.json()
            print_status(f"Task submitted successfully", "SUCCESS")
            print(f"\nTask Details:")
            print(f"  {Colors.BOLD}Run ID:{Colors.ENDC} {result['run_id']}")
            print(f"  {Colors.BOLD}Status:{Colors.ENDC} {result['status']}")
            print(f"  {Colors.BOLD}Created:{Colors.ENDC} {result['created_at']}")
            return result
        else:
            print_status(f"Task submission failed: {response.status_code}", "ERROR")
            print(f"Response: {response.text}")
            return None
    
    except Exception as e:
        print_status(f"Error submitting task: {str(e)}", "ERROR")
        return None


async def poll_task_status(run_id: str, max_polls: int = 10) -> Dict[str, Any]:
    """Poll task status until completion or approval needed"""
    print_section("STEP 3: Poll Task Status")
    
    print_status(f"Polling task {run_id}", "INFO")
    print_status(f"Max polls: {max_polls}, interval: 2 seconds", "INFO")
    
    for poll_count in range(1, max_polls + 1):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_BASE_URL}/status/{run_id}",
                    headers={"Authorization": AUTH_TOKEN},
                    timeout=10.0
                )
            
            if response.status_code == 200:
                status_data = response.json()
                current_status = status_data.get("status")
                
                # Format output
                status_symbol = {
                    "submitted": "⏳",
                    "processing": "⚙️",
                    "awaiting_approval": "⚠️",
                    "completed": "✅",
                    "failed": "❌"
                }.get(current_status, "❓")
                
                print(f"\n{Colors.BOLD}Poll #{poll_count}{Colors.ENDC} - {status_symbol} {current_status.upper()}")
                print(f"  Current Node: {status_data.get('current_node', 'N/A')}")
                print(f"  Progress: {status_data.get('progress', 'N/A')}")
                
                # Check if approval is needed
                if status_data.get("requires_approval"):
                    print_status("Task requires human approval!", "WARNING")
                    return status_data
                
                # Check if completed
                if current_status in ["completed", "failed"]:
                    print_status(f"Task {current_status}", "SUCCESS" if current_status == "completed" else "ERROR")
                    if status_data.get("result"):
                        print(f"\nResult:\n{json.dumps(status_data['result'], indent=2)}")
                    return status_data
                
                # Wait before next poll
                if poll_count < max_polls:
                    await asyncio.sleep(2)
            
            else:
                print_status(f"Status check failed: {response.status_code}", "ERROR")
                return None
        
        except Exception as e:
            print_status(f"Error polling status: {str(e)}", "ERROR")
            return None
    
    print_status("Max polls reached without completion", "WARNING")
    return None


async def approve_task(run_id: str, approved: bool = True) -> bool:
    """Approve or reject a task waiting for human decision"""
    print_section("STEP 4: Approval Decision (HITL)")
    
    action = "APPROVE" if approved else "REJECT"
    print_status(f"{action}ing task {run_id}", "INFO")
    
    payload = {
        "approved": approved,
        "reason": "Demo approval - testing workflow" if approved else "Demo rejection - testing workflow",
        "notes": "This approval was made by the demo flow script"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/approve/{run_id}",
                json=payload,
                headers={"Authorization": AUTH_TOKEN},
                timeout=10.0
            )
        
        if response.status_code == 200:
            result = response.json()
            print_status(f"Approval recorded successfully", "SUCCESS")
            print(f"\nApproval Details:")
            print(f"  {Colors.BOLD}Status:{Colors.ENDC} {result['status']}")
            print(f"  {Colors.BOLD}Message:{Colors.ENDC} {result['message']}")
            print(f"  {Colors.BOLD}Approved At:{Colors.ENDC} {result['approved_at']}")
            return True
        else:
            print_status(f"Approval failed: {response.status_code}", "ERROR")
            print(f"Response: {response.text}")
            return False
    
    except Exception as e:
        print_status(f"Error submitting approval: {str(e)}", "ERROR")
        return False


async def run_demo_flow():
    """Run the complete demo flow"""
    
    print("\n")
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║              🤖 AGENTIC OS - DEMO FLOW                       ║
    ║                                                               ║
    ║  This script demonstrates the complete workflow:             ║
    ║  1. Health check                                              ║
    ║  2. Task submission                                           ║
    ║  3. Status polling                                            ║
    ║  4. Approval (if needed)                                      ║
    ║  5. Completion                                                ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    print(Colors.ENDC)
    
    # Step 1: Health check
    if not await check_health():
        print_status("API is not available. Aborting demo.", "ERROR")
        return
    
    # Step 2: Submit task
    task = await submit_task(
        "Create a customer refund for order #12345 due to product defect"
    )
    
    if not task:
        print_status("Task submission failed. Aborting demo.", "ERROR")
        return
    
    run_id = task["run_id"]
    
    # Step 3: Poll for status
    status = await poll_task_status(run_id, max_polls=10)
    
    if not status:
        print_status("Could not retrieve task status. Aborting demo.", "ERROR")
        return
    
    # Step 4: Handle approval if needed
    if status.get("requires_approval"):
        print_status("Waiting 3 seconds before approving...", "INFO")
        await asyncio.sleep(3)
        
        await approve_task(run_id, approved=True)
        
        # Continue polling after approval
        print_status("Resuming status polling after approval...", "INFO")
        await asyncio.sleep(2)
        status = await poll_task_status(run_id, max_polls=5)
    
    # Final summary
    print_section("DEMO FLOW COMPLETED")
    print_status("Demo flow finished successfully", "SUCCESS")
    print(f"\nFinal Status:")
    print(f"  {Colors.BOLD}Run ID:{Colors.ENDC} {run_id}")
    print(f"  {Colors.BOLD}Status:{Colors.ENDC} {status.get('status') if status else 'Unknown'}")
    print(f"  {Colors.BOLD}Timestamp:{Colors.ENDC} {datetime.now().isoformat()}")
    
    print(f"\n{Colors.BOLD}Next Steps:{Colors.ENDC}")
    print("  1. Check logs/app.log for detailed execution logs")
    print("  2. View logs/traces.jsonl for execution traces")
    print("  3. Review logs/metrics.json for system metrics")
    print(f"  4. Visit {API_BASE_URL}/docs for API documentation")
    print(f"\n{Colors.BOLD}Test Different Scenarios:{Colors.ENDC}")
    print("  • Modify the task description to trigger different agents")
    print("  • Try rejecting the approval to see error handling")
    print("  • Submit multiple tasks concurrently")


# ============================================================================
# ALTERNATIVE DEMO SCENARIOS
# ============================================================================

async def demo_scenario_research():
    """Demo scenario: Research task"""
    print_section("DEMO SCENARIO: Research Task")
    
    if not await check_health():
        return
    
    task = await submit_task(
        "Research the top 5 AI companies by market cap and provide a brief summary of each"
    )
    
    if task:
        status = await poll_task_status(task["run_id"], max_polls=5)
        if status:
            print_status("Research task completed", "SUCCESS")


async def demo_scenario_error():
    """Demo scenario: Task that should fail"""
    print_section("DEMO SCENARIO: Error Handling")
    
    if not await check_health():
        return
    
    task = await submit_task(
        "Delete all customer records"  # This should trigger security checks
    )
    
    if task:
        status = await poll_task_status(task["run_id"], max_polls=5)
        if status:
            print_status(f"Task finished with status: {status.get('status')}", "INFO")


# ============================================================================
# MAIN ENTRY
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        scenario = sys.argv[1]
        if scenario == "research":
            asyncio.run(demo_scenario_research())
        elif scenario == "error":
            asyncio.run(demo_scenario_error())
        else:
            print(f"Unknown scenario: {scenario}")
            print("Available scenarios: research, error")
    else:
        # Run default flow
        asyncio.run(run_demo_flow())