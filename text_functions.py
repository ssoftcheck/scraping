import pandas
import re
import string
from nltk import word_tokenize
from nltk.stem import WordNetLemmatizer,porter

def print_top_words(model, feature_names, n_top_words):
    for topic_idx, topic in enumerate(model.components_):
        print("Topic #%d:" % topic_idx)
        print(",".join(feature_names[i]))
        for i in topic.argsort()[:-n_top_words - 1:-1]:
            print(i)
            
def top_words(model,feature_names,n_top_words):
    topics = []
    terms = []
    for topic_idx, topic in enumerate(model.components_):
        topics.append(topic_idx)
        terms.append(','.join([feature_names[i] for i in topic.argsort()[:-n_top_words - 1:-1]]))
    return pandas.DataFrame({'topic':topics,'terms':terms},columns=['topic','terms'])    

def no_punct(txt):
    punct_list = string.punctuation + '’' + '”' + '“'
    for punct in punct_list:
        if txt.startswith('not_'):
            txt = txt[:4] + txt[4:].replace(punct,' ')
        else:
            txt = txt.replace(punct,' ')
    return txt

def no_number(txt):
    return re.sub(r'(\$\s*)?\d+[\.,\d]*','',txt)

def add_negation(x):
    pattern = r'not? +(\w+)'
    repl = r'not_\1'
    q = re.sub(pattern,repl,x,flags=re.IGNORECASE)
    
    pattern = r'n\'t +(\w+)'
    repl = r' not_\1'
    q = re.sub(pattern,repl,q,flags=re.IGNORECASE)
    
    return q

class Tokenizer():
    def __init__(self, negation = True, excludePunct=True, excludeNum=True,tokenizer='lemma', ignore=None):
        if tokenizer not in ['lemma','porter']:
            raise Exception('{} is not a supported tokeinzer, choose "lemma" or "porter"'.format(self.tokenizer))
        self.negation = negation
        self.excludePunct = excludePunct
        self.excludeNum = excludeNum
        self.tokenizer = tokenizer
        if ignore is None:
            self.ignore = []
        else:
            self.ignore = ignore
    
    def process(self, doc):
        if self.negation:
            doc = add_negation(doc)
        if self.excludePunct:
            doc = no_punct(doc)  
        if self.tokenizer == 'lemma':
            token_maker = WordNetLemmatizer()
            tokens = [token_maker.lemmatize(t) if t not in self.ignore else t for t in word_tokenize(doc)]
        elif self.tokenizer == 'porter':
            token_maker = porter.PorterStemmer()
            tokens = [token_maker.stem(t) if t not in self.ignore else t for t in word_tokenize(doc)]
        if self.excludeNum:
            tokens = [no_number(l) for l in tokens]
        tokens = list(map(lambda x: x.strip(), filter(lambda x: len(x) > 0,tokens)))
        return tokens