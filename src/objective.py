# Copyright 2020 The `Kumar Nityan Suman` (https://github.com/nityansuman/). All Rights Reserved.
#
#                     GNU GENERAL PUBLIC LICENSE
#                        Version 3, 29 June 2007
#  Copyright (C) 2007 Free Software Foundation, Inc. <http://fsf.org/>
#  Everyone is permitted to copy and distribute verbatim copies
#  of this license document, but changing it is not allowed.
# ==============================================================================

import logging
import re

import nltk
import numpy as np
from nltk.corpus import wordnet as wn


class ObjectiveTest:
	"""Class abstraction for objective test generation module.
	"""

	def __init__(self, filepath: str):
		"""Class constructor.

		Args:
			filepath (str): Absolute path to the corpus file.
				The corpus is used to generate test.
		"""
		# Load subject corpus
		try:
			with open(filepath, mode="r") as fp:
				self.summary = fp.read()
		except FileNotFoundError:
			logging.exception("Corpus file not found.", exc_info=True)
		else:
			logging.info("Corpus file load successful.")

	def generate_test(self, num_questions: int = 3) -> list, list:
		"""Method to generate an objective test.

		Args:
			num_questions (int, optional): Number of questions in a test.

		Returns:
			list, list: Questions and answer options respectively.
		"""
		# Identify potential question sets
		question_sets = self.get_question_sets()

		# Identify potential question answers
		question_answers = list()
		for question_set in question_sets:
			if question_set["Key"] > 3:
				question_answers.append(question_set)

		# Create objective test set
		questions, answers = list(), list()
		while len(questions) < num_questions:
			rand_num = np.random.randint(0, len(question_answers))
			if question_answers[rand_num]["Question"] not in questions:
				questions.append(question_answers[rand_num]["Question"])
				answers.append(question_answers[rand_num]["Answer"])
		return questions, answers

	def get_question_sets(self) -> list:
		"""Method to dentify sentences with potential objective questions.

		Returns:
			list: Sentences with potential objective questions.
		"""
		# Tokenize corpus into sentences
		try:
			sentences = nltk.sent_tokenize(self.summary)
		except Exception:
			logging.exception("Sentence tokenization failed.", exc_info=True)
		else:
			logging.info("Sentence tokenization successful.")

		# Identify potential question sets
		# Each question set consists:
		# 	Question: Objective question.
		# 	Answer: Actual asnwer.
		#	Key: Other options.
		question_sets = list()
		for sent in sentences:
			question_set = self.identify_potential_questions(sent)
			if question_set is not None:
				question_sets.append(question_set)
		return question_sets

	def identify_potential_questions(self, sentence: str) -> dict:
		"""Method to identiyf potential question sets.

		Args:
			sentence (str): Tokenized sequence from corpus.

		Returns:
			dict: Question formed along with the correct answer in case of
				potential sentence else return None.
		"""
		# POS tag sequences
		tags = nltk.pos_tag(sentence)
		if tags[0][1] == "RB" or len(nltk.word_tokenize(sentence)) < 4:
			return None

		# Create regex grammer
		noun_phrases = list()
		grammer = r"""
			CHUNK: {<NN>+<IN|DT>*<NN>+}
				{<NN>+<IN|DT>*<NNP>+}
				{<NNP>+<NNS>*}
			"""

		# Create parser tree
		chunker = nltk.RegexpParser(grammer)
		tokens = nltk.word_tokenize(sentence)
		pos_tokens = nltk.tag.pos_tag(tokens)
		tree = chunker.parse(pos_tokens)

		# Parse tree to identify tokens
		for subtree in tree.subtrees():
			if subtree.label() == "CHUNK":
				temp = ""
				for sub in subtree:
					temp += sub[0]
					temp += " "
				temp = temp.strip()
				noun_phrases.append(temp)

		# Handle nouns
		replace_nouns = []
		for word, _ in tags:
			for phrase in noun_phrases:
				if phrase[0] == '\'':
					# If it starts with an apostrophe, ignore it
					# (this is a weird error that should probably be handled elsewhere)
					break
				if word in phrase:
					# Blank out the last two words in this phrase
					[replace_nouns.append(phrase_word) for phrase_word in phrase.split()[-2:]]
					break
			# If we couldn't find the word in any phrases
			if len(replace_nouns) == 0:
				replace_nouns.append(word)
			break

		if len(replace_nouns) == 0:
			return None

		val = 99
		for i in replace_nouns:
			if len(i) < val:
				val = len(i)
			else:
				continue

		trivial = {
			"Answer": " ".join(replace_nouns),
			"Key": val
		}

		if len(replace_nouns) == 1:
			# If we're only replacing one word, use WordNet to find similar words
			trivial["Similar"] = self.answer_options(replace_nouns[0])
		else:
			# If we're replacing a phrase, don't bother - it's too unlikely to make sense
			trivial["Similar"] = []

		replace_phrase = " ".join(replace_nouns)
		blanks_phrase = ("__________" * len(replace_nouns)).strip()
		expression = re.compile(re.escape(replace_phrase), re.IGNORECASE)
		sentence = expression.sub(blanks_phrase, str(sentence), count=1)
		trivial["Question"] = sentence
		return trivial

	@staticmethod
	def answer_options(word: str) -> list:
		"""Method to identify incorrect answer options.

		Arguments:
			word (str): Actual answer to the question which is to be used
				for generating other deceiving options.

		Returns:
			list: Answer options.
		"""
		# In the absence of a better method, take the first synset
		synsets = wn.synsets(word, pos="n")

		# If there aren't any synsets, return an empty list
		if len(synsets) == 0:
			return []
		else:
			synset = synsets[0]

		# Get the hypernym for this synset (again, take the first)
		hypernym = synset.hypernyms()[0]

		# Get some hyponyms from this hypernym
		hyponyms = hypernym.hyponyms()

		# Take the name of the first lemma for the first 8 hyponyms
		similar_words = []
		for hyponym in hyponyms:
			similar_word = hyponym.lemmas()[0].name().replace("_", " ")
			if similar_word != word:
				similar_words.append(similar_word)
			if len(similar_words) == 8:
				break
		return similar_words
