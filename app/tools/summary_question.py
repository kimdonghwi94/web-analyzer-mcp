from app.tools import build_output
from app.tools.gpt_api import summarize_text


def summary_question(url: str, question: str):
    """
    Summarizes the provided question based on given URL information.

    This function retrieves relevant data from the given URL and uses it to
    generate a summarized answer to the specified question.

    Args:
        url: str
            The URL from which information will be gathered.
        question: str
            The question that needs to be answered based on the URL's content.

    Returns:
        str: The summarized answer to the question.
    """
    rag = build_output(url)
    answer = summarize_text(question,rag)

    return answer
