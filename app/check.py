def load_words_from_whitespace_file(filename):
    with open(filename, 'r') as file:
        # Read the entire file content as one big string
        content = file.read()
        
        # Split by all whitespace (spaces, tabs, newlines).
        # This returns a list of words, removing empty strings.
        words = content.split(",")
        
        # Optionally convert all words to lowercase for consistent checking
        words = [word.lower() for word in words]
        
    return words

filename = './app/words.txt' # Change this to your actual file name
word_list = load_words_from_whitespace_file(filename)

# Now, you can run the duplicate check (Method 2 from my previous answer):
single_words = []
from collections import Counter
word_counts = Counter(word_list)
for word, count in word_counts.items():
    if count == 1:
        single_words.append

duplicate_words = {word: count for word, count in word_counts.items() if count > 1}

print(f"Total words found: {len(word_list)}")
print(f"Total unique words: {len(word_counts)}")

if duplicate_words:
    print("Duplicates found:", duplicate_words)
else:
    print("No duplicates found.")