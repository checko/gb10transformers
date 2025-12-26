from transformers import pipeline

# This automatically downloads a model and its tokenizer
classifier = pipeline("sentiment-analysis")
print(classifier("I hate learning about AI!"))
