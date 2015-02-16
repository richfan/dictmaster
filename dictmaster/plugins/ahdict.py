# -*- coding: utf-8 -*-

import re
import os

from pyquery import PyQuery as pq
from lxml import etree

from dictmaster.util import html_container_filter
from dictmaster.pthread import PluginThread
from dictmaster.fetcher import WordFetcher
from dictmaster.postprocessor import HtmlContainerProcessor
from dictmaster.editor import Editor

# TODO: get full word list

class Plugin(PluginThread):
    def __init__(self, popts, dirname):
        word_file = popts
        if not os.path.exists(word_file):
            sys.exit("Provide full path to (existing) word list file!")
        super(Plugin, self).__init__(popts, dirname)
        self.dictname = "The American Heritage Dictionary of the English Language, Fifth Edition"
        fetcher = AhdictFetcher(
            self.output_directory,
            url_pattern="https://ahdictionary.com/word/search.html?q={word}",
            word_file=word_file,
            word_codec=("utf-8", "utf-8")
        )
        postprocessor = AhdictProcessor("td", self)
        editor = Editor(
            output_directory=self.output_directory,
            plugin=self
        )
        self._stages = [
            fetcher,
            postprocessor,
            editor
        ]

class AhdictFetcher(WordFetcher):
    class FetcherThread(WordFetcher.FetcherThread):
        filter_data = html_container_filter("#results", bad_content="No word definition found")

class AhdictProcessor(HtmlContainerProcessor):
    def do_pre_html(self, encoded_str):
        regex = [
            # pronunciation
            [r"","′"],
            [r"","o͞o"],
            [r"</?font[^>]*>",""]
        ]
        for r in regex:
            encoded_str = re.sub(r[0], r[1], encoded_str)
        return encoded_str

    def do_html_term(self, doc):
        term = doc("b").eq(0).text().strip()
        regex = [
            [r"\xb7",""], # the centered dot
            [r" ([0-9]+)$",r"(\1)"]
        ]
        for r in regex:
            term = re.sub(r[0], r[1], term)
        return term

    def do_html_definition(self, html, term):
        doc = pq(html)
        doc("img").remove()
        doc("div[align=right]").remove()
        doc("a").removeAttr("name")
        doc("a").removeAttr("target")
        for a in html.find("a:not([href])"):
            if doc(a).text().strip() == "":
                doc(a).remove()
            else:
                doc(a).replaceWith(doc(a).html())
        for a in html.find("a"):
            if doc(a).text().strip() == "":
                doc(a).remove()
            elif "search.html" not in doc(a).attr("href"):
                doc(a).replaceWith(doc(a).html())
            else:
                href = "bword://%s" % doc(a).text().strip(". ").lower()
                doc(a).attr("href", href)
        doc("div.rtseg b").css("color","#069")
        doc("i").css("color","#940")
        doc("div.pseg > i").css("color","#900")
        doc("div.runseg > i").css("color","#900")
        for div in html.find("div.ds-list"):
            doc(div).replaceWith(
                doc("<p/>").html(doc(div).html()).outerHtml()
            )
        for div in html.find("div.sds-list"):
            doc(div).replaceWith(
                doc("<p/>").css("margin-left","1ex")
                    .html(doc(div).html()).outerHtml()
            )
        html.find("*").removeAttr("class").removeAttr("title")
        for span in html.find("span"):
            doc(span).replaceWith(doc(span).html())

        return html.html().strip()
