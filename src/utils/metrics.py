class Metrics:

    def __init__(self):
        self.reset()

    def reset(self):
        self.data = {
            # LLM
            "llm_calls": 0,
            "llm_calls_by_model": {},
            "llm_retries": 0,

            # Token usage
            "input_tokens": 0,
            "output_tokens": 0,

            # Cost tracking
            "cost_per_model": {},
            "total_cost": 0.0,

            # Retrieval
            "retrieval_calls": 0,
            "chunks_retrieved": 0,
            "chunks_after_filter": 0,

            # OCR
            "ocr_attempts": 0,
            "ocr_success": 0,
            "ocr_fail": 0,
        }

        # Pricing (USD per 1K tokens)
        self.MODEL_PRICING = {
            "llama-3.3-70b-versatile": {
                "input_per_1k": 0.00059,
                "output_per_1k": 0.00079
            },
            "llama-3.1-8b-instant": {
                "input_per_1k": 0.00020,
                "output_per_1k": 0.00030
            },
            "anthropic/claude-3-haiku": {
                "input_per_1k": 0.00025,
                "output_per_1k": 0.00125
            },
            "openai/gpt-4o-mini": {
                "input_per_1k": 0.00015,
                "output_per_1k": 0.00060
            },
            "gemini-2.5-flash": {
                "input_per_1k": 0.00035,
                "output_per_1k": 0.00070
            }
        }

    # -------------------------
    # Generic increment
    # -------------------------
    def inc(self, key, amount=1):
        if key not in self.data:
            self.data[key] = 0
        self.data[key] += amount

    # -------------------------
    # LLM tracking
    # -------------------------
    def inc_model(self, model_name: str):
        self.data["llm_calls"] += 1

        if model_name not in self.data["llm_calls_by_model"]:
            self.data["llm_calls_by_model"][model_name] = 0

        self.data["llm_calls_by_model"][model_name] += 1

    def inc_retry(self):
        self.data["llm_retries"] += 1

    # -------------------------
    # Token tracking
    # -------------------------
    def add_tokens(self, input_tokens: int, output_tokens: int):
        self.data["input_tokens"] += input_tokens
        self.data["output_tokens"] += output_tokens

    # -------------------------
    # Cost tracking
    # -------------------------
    def add_cost(self, model_name: str, input_tokens: int, output_tokens: int):

        pricing = self.MODEL_PRICING.get(model_name)

        if not pricing:
            return

        input_cost = (input_tokens / 1000) * pricing["input_per_1k"]
        output_cost = (output_tokens / 1000) * pricing["output_per_1k"]

        total = input_cost + output_cost

        if model_name not in self.data["cost_per_model"]:
            self.data["cost_per_model"][model_name] = 0.0

        self.data["cost_per_model"][model_name] += total
        self.data["total_cost"] += total

    # -------------------------
    # Logging
    # -------------------------
    def log(self, logger):
        logger.info("========== METRICS SUMMARY ==========")

        for key, value in self.data.items():
            logger.info(f"{key}: {value}")

        logger.info("=====================================")


# GLOBAL SINGLETON
metrics = Metrics()