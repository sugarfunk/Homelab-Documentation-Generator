"""Prompt templates for LLM-powered documentation generation."""

from typing import Dict, Any, Optional


def generate_service_explanation(service_name: str, service_data: Dict[str, Any]) -> str:
    """Generate a prompt for explaining a service.

    Args:
        service_name: Name of the service
        service_data: Service configuration data

    Returns:
        Prompt string
    """
    image = service_data.get('image', 'unknown')
    ports = service_data.get('ports', [])
    environment = service_data.get('environment', {})

    prompt = f"""You are a technical documentation expert. Please provide a clear, concise explanation of this self-hosted service.

Service Name: {service_name}
Docker Image: {image}
Exposed Ports: {', '.join(map(str, ports)) if ports else 'None'}

Context:
- This is part of a self-hosted homelab infrastructure
- The explanation should be understandable by someone familiar with Docker but not necessarily this specific service

Please provide:
1. A 2-3 sentence summary of what this service does
2. The primary purpose/use case (why would someone use this?)
3. Key features or capabilities

Keep the response under 200 words and focus on practical information."""

    return prompt


def generate_troubleshooting_guide(
    service_name: str,
    service_type: Optional[str],
    common_issues: Optional[list] = None
) -> str:
    """Generate a prompt for creating troubleshooting guide.

    Args:
        service_name: Name of the service
        service_type: Type of service (e.g., "database", "web server")
        common_issues: Known common issues

    Returns:
        Prompt string
    """
    prompt = f"""You are a systems administrator creating troubleshooting documentation.

Service: {service_name}
Type: {service_type or 'Unknown'}

Please create a troubleshooting guide with:

1. **Common Symptoms** (3-5 items)
   - What a user would notice when something is wrong

2. **Quick Checks** (3-5 items)
   - First things to check when troubleshooting
   - Include specific commands where applicable

3. **Common Solutions** (3-5 items)
   - Step-by-step fixes for typical problems
   - Include Docker commands (restart, logs, etc.)

4. **When to Escalate**
   - Signs that the problem requires advanced troubleshooting

Keep it practical and focused on Docker-based services. Include actual command examples.
Format the response in markdown.

Maximum 400 words."""

    if common_issues:
        prompt += f"\n\nKnown Issues:\n" + "\n".join(f"- {issue}" for issue in common_issues)

    return prompt


def generate_plain_english_summary(service_name: str, technical_description: str) -> str:
    """Generate a non-technical summary.

    Args:
        service_name: Name of the service
        technical_description: Technical description

    Returns:
        Prompt string
    """
    prompt = f"""You are explaining technology to someone with no technical background.

Service: {service_name}
Technical Description: {technical_description}

Please rewrite this as a plain-English explanation that would make sense to someone who:
- Doesn't know what Docker is
- Has minimal computer knowledge
- Just needs to understand what this service does and why it matters

Use everyday language and avoid jargon. If you must use a technical term, explain it simply.
Maximum 150 words.

Focus on:
- What problem it solves
- What you can do with it
- Why it's useful"""

    return prompt


def generate_analogy(service_name: str, service_description: str) -> str:
    """Generate an analogy to explain the service.

    Args:
        service_name: Name of the service
        service_description: Service description

    Returns:
        Prompt string
    """
    prompt = f"""Create a simple, relatable analogy to explain this technology.

Service: {service_name}
Description: {service_description}

Create a 2-3 sentence analogy comparing this service to something in everyday life.
The analogy should help a non-technical person understand what the service does.

Example format: "Think of {service_name} like a [everyday object]. Just as [everyday object does X],
{service_name} [does Y]."

Make it simple, memorable, and accurate."""

    return prompt


def generate_procedure(
    procedure_type: str,
    context: Dict[str, Any],
    for_non_technical: bool = False
) -> str:
    """Generate a step-by-step procedure.

    Args:
        procedure_type: Type of procedure (e.g., "backup", "restore", "update")
        context: Context information
        for_non_technical: If True, generate for non-technical users

    Returns:
        Prompt string
    """
    audience = "non-technical user with basic computer skills" if for_non_technical else "system administrator"

    prompt = f"""Create a step-by-step procedure for: {procedure_type}

Context:
{_format_context(context)}

Audience: {audience}

Please provide:
1. **Prerequisites**
   - What needs to be in place before starting
   - Required access/credentials

2. **Step-by-Step Instructions**
   - Clear, numbered steps
   - Include specific commands if applicable
   - Explain what each step does

3. **Verification**
   - How to confirm the procedure worked

4. **Troubleshooting**
   - What to do if something goes wrong

Format in markdown.
"""

    if for_non_technical:
        prompt += """
IMPORTANT: Use simple language. Explain every command. Don't assume technical knowledge.
For example: Instead of "SSH into the server", say "Connect to the server using the terminal program"."""

    return prompt


def generate_emergency_guide(infrastructure_summary: Dict[str, Any]) -> str:
    """Generate emergency recovery guide.

    Args:
        infrastructure_summary: Summary of infrastructure

    Returns:
        Prompt string
    """
    prompt = f"""You are creating an EMERGENCY GUIDE for someone who needs to manage a homelab infrastructure
in a crisis situation (e.g., the primary administrator is unavailable).

Infrastructure Summary:
{_format_context(infrastructure_summary)}

Create a comprehensive emergency guide with:

1. **START HERE - First 5 Minutes**
   - Immediate actions if everything is down
   - How to check what's working
   - Emergency contacts

2. **Access Everything**
   - Where passwords are stored
   - How to connect to servers
   - How to access the network

3. **Critical Services** (must keep running)
   - What they are and why they matter
   - How to check if they're running
   - How to restart them

4. **Disaster Recovery**
   - Where backups are located
   - How to restore from backup
   - Step-by-step recovery process

5. **When to Get Help**
   - What problems can wait
   - What problems need immediate expert help
   - Who to contact

6. **Monthly Costs**
   - What bills to expect
   - Which services cost money

Format in markdown. Be extremely clear and assume the reader is stressed and non-technical.
Maximum 800 words."""

    return prompt


def generate_glossary_entry(term: str, context: Optional[str] = None) -> str:
    """Generate a glossary entry for a technical term.

    Args:
        term: Technical term
        context: Optional context about how it's used

    Returns:
        Prompt string
    """
    prompt = f"""Create a glossary entry for the technical term: "{term}"

Please provide:
1. **Simple Definition** (1-2 sentences, no jargon)
2. **Technical Definition** (1-2 sentences, for those who want details)
3. **Plain English Analogy** (1 sentence comparing to everyday concept)
4. **Example** (How it's used in this homelab context)

Keep it concise but clear. The goal is to help both technical and non-technical readers."""

    if context:
        prompt += f"\n\nContext: {context}"

    return prompt


def generate_cost_breakdown(services: list, subscriptions: list) -> str:
    """Generate cost analysis and breakdown.

    Args:
        services: List of services with potential costs
        subscriptions: List of known subscriptions

    Returns:
        Prompt string
    """
    prompt = f"""Analyze the costs associated with this homelab infrastructure.

Services: {len(services)} total
Known Subscriptions:
{_format_list(subscriptions)}

Please provide:
1. **Direct Costs**
   - Subscription services and their costs
   - Domain names
   - API usage fees

2. **Estimated Electricity Costs**
   - Based on typical server power consumption
   - Monthly estimate

3. **Replacement/Depreciation**
   - Hardware lifecycle costs

4. **Total Monthly Cost**
   - Breakdown by category

5. **Cost Optimization Tips**
   - Where money could be saved

Be practical and realistic. Format as markdown."""

    return prompt


def _format_context(context: Dict[str, Any]) -> str:
    """Format context dictionary for prompts.

    Args:
        context: Context data

    Returns:
        Formatted string
    """
    lines = []
    for key, value in context.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        elif isinstance(value, dict):
            lines.append(f"{key}:")
            for k, v in value.items():
                lines.append(f"  {k}: {v}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def _format_list(items: list) -> str:
    """Format a list for prompts.

    Args:
        items: List of items

    Returns:
        Formatted string
    """
    if not items:
        return "None"
    return "\n".join(f"- {item}" for item in items)
