from langchain_anthropic import ChatAnthropic

# Initialize Claude client
def init_claude():
    return ChatAnthropic(api_key="your-claude-api-key", model="claude-3-5-sonnet-20241022")

# TODO: Add resume parsing logic
