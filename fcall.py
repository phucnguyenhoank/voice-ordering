from utils import llama

context = "Phuc and Mui are friends. Mui and Huy are friends."

query = "Are Phuc and Huy friends?"

prompt_1 = f"""Given the context: {context}. 
Help me answer the query: {query}. 
Think step by step, and then give me the answer in the form `answer:yes`, or `answer:no`."""

prompt = "I want to eat your fast food for free."

response_1, ctx = llama(prompt)

print(f"[{response_1}]")
print(f"context length: {len(ctx)}")
