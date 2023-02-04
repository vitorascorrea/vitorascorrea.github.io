import os, shutil, json, datetime
from re import sub

from bs4 import BeautifulSoup
from markdown import markdown


class ContentFile:
  def __init__(self, raw_content):
    self.raw_content = raw_content
    self.date, self.title = self.metadata()
    self.html_content = self.html_content()

  def metadata(self):
    metadata = self.raw_content.split("---")[1].split("\n")[1:]
    date = metadata[0].split(": ")[1]
    title = metadata[1].split(": ")[1]

    return date, title

  def html_content(self):
    content = self.raw_content.split("---")[-1]
    return markdown(content)


class BaseFile:
  def __init__(self, raw_content, blog_metadata):
    self.raw_content = raw_content
    self.bs_object = BeautifulSoup(raw_content, features="html.parser")
    self.update_bs_object_with_metadata(blog_metadata)

  def to_string(self):
    stringified = self.bs_object.prettify(formatter=None)

    return stringified

  def update_bs_object_with_metadata(self, metadata):
    self.bs_object.title.string = metadata["title"]
    bio_content_node = self.bs_object.find(id="bio-content")
    bio_content_node.string = metadata["bio"]
    footer_node = self.bs_object.find(id="footer")
    footer_node.string = "© {} - {}".format(datetime.date.today().year, metadata["footer"])


class ArticleFile(BaseFile):
  def __init__(self, raw_content, blog_metadata):
    super().__init__(raw_content, blog_metadata)
    self.title = ""
    self.date = ""
    self.excerpt = ""

  def update_article_title(self, title):
    article_title_node = self.bs_object.find(id="article-title")
    article_title_node.string = title
    self.title = title

  def update_date(self, date):
    article_date_node = self.bs_object.find(id="date")
    article_date_node.string = date
    self.date = date

  def update_content(self, markdown_content):
    html_content = markdown(markdown_content)
    article_content_node = self.bs_object.find(id="content")
    article_content_node.string = html_content
    self.excerpt = html_content


class IndexFile(BaseFile):
  def add_articles(self, articles):
    article_list_node = self.bs_object.find(id = "article-list")
    articles_raw_strings = []

    for file_name, article in articles.items():
      articles_raw_strings.append("""
      <li>
        <article class="article-summary">
          <header>
            <h2 class="small-title title">
              <a href="{file_name}.html">{title}</a>
            </h2>
            <small>{date}</small>
          </header>
          <section>
            <p class="article-excerpt">
              {excerpt}
            </p>
          </section>
        </article>
      </li>
      """.format(
        file_name = file_name,
        title = article.title,
        date = article.date,
        excerpt = article.excerpt
      ))

    article_list_node.string = "".join(articles_raw_strings)


class Writer:
  def __init__(self, index, articles):
    self.index = index
    self.articles = articles

  def write_files(self):
    self.clear_docs_folder()
    self.write_index()
    self.write_articles()
    self.copy_assets()

  def clear_docs_folder(self):
    shutil.rmtree("docs", ignore_errors=False, onerror=None)
    os.mkdir("docs")

  def write_index(self):
    f = open("docs/index.html", "x")
    f.write(self.index.to_string())
    f.close()

  def write_articles(self):
    for file_name, article in self.articles.items():
      f = open("docs/{}.html".format(file_name), "x")
      f.write(article.to_string())
      f.close()

  def copy_assets(self):
    shutil.copyfile("ssg/template/stylesheet.css", "docs/stylesheet.css")


class Compiler:
  def snake_case(self, s):
    return '_'.join(
      sub('([A-Z][a-z]+)', r' \1',
      sub('([A-Z]+)', r' \1',
      s.replace('-', ' '))).split()).lower()


  def get_file_string_content(self, path):
    file = open(path, "r")
    content = file.read()
    file.close()

    return content


  def get_content_files(self):
    content_files = []
    content_root = "content"
    metadata = None

    for root, _, files in os.walk(content_root):
      for file_name in files:
        path = os.path.join(root, file_name)

        if "metadata" in file_name:
          metadata = self.get_file_string_content(path)
        else:
          content_files.append(
            ContentFile(self.get_file_string_content(path))
          )

    content_files.sort(key=lambda c: c.date, reverse=True)

    return metadata, content_files


  def get_template_files(self):
    template_files = {}
    template_root = "ssg/template"

    for root, dirs, files in os.walk(template_root):
      for file_name in files:
        if ".html" in file_name:
          template_files[file_name] = self.get_file_string_content(os.path.join(root, file_name))

    return template_files


  def compile(self):
    # get all template files and convert them to beautifulsoup
    template_files = self.get_template_files()
    # get all content files, including metadata
    metadata, content_files = self.get_content_files()

    articles = {}
    blog_metadata = json.loads(metadata)

    for content_file in content_files:
      article_file = ArticleFile(template_files["article.html"], blog_metadata)

      article_file.update_article_title(content_file.title)
      article_file.update_date(content_file.date)
      article_file.update_content(content_file.html_content)

      articles[self.snake_case(content_file.title)] = article_file

    index = IndexFile(template_files["index.html"], blog_metadata)
    index.add_articles(articles)

    Writer(index, articles).write_files()


if __name__ == "__main__":
  Compiler().compile()





