UsageDetails = dict[str, int]


def usage_details_from_openai(usage: object | None) -> UsageDetails | None:
    if usage is None:
        return None

    prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    total_tokens = int(getattr(usage, "total_tokens", 0) or 0)

    if prompt_tokens == 0 and completion_tokens == 0 and total_tokens == 0:
        return None

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def usage_details_from_langchain(usage_metadata: dict[str, int] | None) -> UsageDetails | None:
    if not usage_metadata:
        return None

    input_tokens = int(usage_metadata.get("input_tokens") or 0)
    output_tokens = int(usage_metadata.get("output_tokens") or 0)
    total_tokens = int(usage_metadata.get("total_tokens") or input_tokens + output_tokens)

    if input_tokens == 0 and output_tokens == 0 and total_tokens == 0:
        return None

    return {
        "input": input_tokens,
        "output": output_tokens,
        "total": total_tokens,
    }
