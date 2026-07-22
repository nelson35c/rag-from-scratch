"""
My RAG knowledge base: notes from building this project from scratch.

Each entry is one document. The chunker will split longer ones into
overlapping pieces labelled base_id#1, base_id#2, and so on.
"""

DEFAULT_DOCUMENTS = [
    {
        "base_id": "embeddings",
        "source": "notes/embeddings.md",
        "text": """An embedding turns a piece of text into a list of numbers that
        capture its meaning. In this project every embedding is a list of exactly
        1536 numbers, produced by the model gemini-embedding-001 through Google's
        OpenAI-compatible endpoint. That model returns 3072 numbers by default, so
        the code passes dimensions=1536 to truncate it. This works without losing
        quality because the model is trained with Matryoshka representation
        learning, where the first part of the vector is still a valid smaller
        version of the whole.

        One embedding call returns one vector, no matter how long the input is. A
        single word becomes 1536 numbers, and a whole paragraph also becomes 1536
        numbers. The model blends the entire input into one fingerprint of meaning.
        Longer and more mixed text produces a blurrier fingerprint, which is the
        reason documents are split into chunks before embedding.

        Similarity between two embeddings is measured with cosine similarity, which
        is the dot product of the two vectors divided by the product of their
        lengths. The result is the cosine of the angle between them. A score near
        1.0 means nearly identical meaning, a score near 0 means unrelated, and a
        score near -1 means opposite. Dividing by the lengths cancels out the size
        of the vectors so only direction matters, which is why a long document and
        a short sentence about the same topic still score as similar.

        The most important rule about embeddings is consistency. Documents and
        questions must be embedded with the same model and the same number of
        dimensions, because vectors are only comparable inside one model's space.
        Changing the embedding model later means re-embedding and re-seeding
        everything from scratch.""",
    },
    {
        "base_id": "chunking",
        "source": "notes/chunking.md",
        "text": """Chunking splits a long document into smaller overlapping pieces
        before embedding. It exists because one embedding call blends all of its
        input into a single fingerprint. Embedding an entire long document produces
        a blurry average of every topic in it, so a question about one specific
        detail will not match it well. Small focused chunks keep each fingerprint
        sharp and searchable.

        The chunker in this project is word based. It cleans the text with a regular
        expression that collapses all runs of whitespace into single spaces, trims
        the ends with strip, and then splits the text into a list of words. It walks
        a sliding window across that list. The window is chunk_size words wide, and
        after each chunk the start position moves forward to the end of that chunk
        minus the overlap. The defaults are 300 words per chunk with 45 words of
        overlap, which is roughly 400 tokens and 60 tokens since one token is about
        0.75 words.

        Overlap is insurance against splitting a sentence in half. Without it, a key
        sentence sitting exactly on a boundary would be cut in two, and neither
        chunk would contain the complete thought, so neither would match a question
        about it. With overlap, any straddling sentence appears whole in at least
        one chunk.

        Every chunk gets an id in the form base_id#number, such as returns#1 and
        returns#2. The part before the hash says which document it came from and the
        part after says which piece it is. This naming is used later by the
        retrieval step to avoid taking several chunks from the same document, and it
        is also what the AI cites in its answers.""",
    },
    {
        "base_id": "vectordb",
        "source": "notes/vector_database.md",
        "text": """The vector database is Supabase, which is hosted Postgres with the
        pgvector extension enabled. Chunks live in a table called rag_chunks with the
        columns id, chunk_id, source, text, embedding, and created_at. The embedding
        column has the type vector(1536), which must match the 1536 dimensions
        produced by the embedding model, or inserts fail with a dimension error.

        Searching is done by a SQL function called match_chunks that lives inside the
        database. It takes a query_embedding and a match_count, compares the query
        vector against every stored embedding, and returns the closest rows sorted
        best first. The comparison uses the pgvector operator <=>, which is cosine
        distance. Since distance and similarity are opposites, the function computes
        1 minus the distance and labels the result with "as similarity".

        The similarity value is not a stored column and never appears in the table.
        It is calculated fresh for every search and thrown away afterwards. It cannot
        be stored because it only means something relative to a specific question.
        The same chunk scores 0.71 against one question and 0.12 against another, so
        there is no single value that could live in a cell.

        Python calls that SQL function with supabase.rpc, which stands for remote
        procedure call and means run a function that lives in the database. The
        comparison happens next to the data instead of downloading every vector to
        the laptop, which is far faster. Simple row operations use a different style,
        supabase.table(...).upsert(...), where upsert with on_conflict set to
        chunk_id means insert the row or overwrite it if that chunk_id already
        exists, so re-seeding never creates duplicates. Every Supabase command must
        end with .execute() or nothing is actually sent.""",
    },
    {
        "base_id": "pipeline",
        "source": "notes/rag_pipeline.md",
        "text": """RAG stands for Retrieval Augmented Generation, and each letter is a
        step in the pipeline. Retrieval embeds the user's question and searches the
        database for the closest chunks. Augmentation builds a context block out of
        those chunks and inserts it into the prompt. Generation sends that enriched
        prompt to the chat model, which writes the answer.

        The key insight is that the AI model never learned anything about this
        private data. It only knows what is pasted into the prompt. The database,
        the embeddings, and the search all exist for one purpose, which is deciding
        which paragraphs go into that prompt.

        Retrieval fetches the top 6 chunks. A helper called pick_best then filters
        them down to at most 4, keeping only one chunk per source document. It does
        this by splitting each chunk_id on the hash character and taking the part
        before it, then tracking which documents have already been used in a set.
        This buys breadth, because otherwise one long chatty document could fill the
        whole context and crowd out other sources.

        The context block is built by joining each chunk as "[chunk_id] text" with
        blank lines between them. Those square bracket labels are what make citations
        possible, since the model can only cite labels that it was given.

        The system prompt is the guardrail and the highest leverage text in the whole
        project. Its rules say to use only facts found in the context, to cite the
        source after each fact, to admit not knowing when the context does not
        contain the answer, and to be concise. The rule that allows the model to say
        it does not know is what prevents hallucination. Temperature is set to 0.1,
        which keeps answers factual and predictable rather than creative.""",
    },
    {
        "base_id": "troubleshooting",
        "source": "notes/troubleshooting.md",
        "text": """ModuleNotFoundError after installing a package almost always means
        pip and python ran in different environments. On this Mac there are three
        competing Python installations: the system Python, an Anaconda base
        environment that auto-activates and shows (base) in the prompt, and the
        project's own virtual environment. If the prompt shows (base) instead of
        (venv), pip install puts packages into conda while the script runs under the
        venv, so the import fails. The check is to run "which python" and "which
        pip" and confirm both paths contain /rag-project/venv/. The fix is to run
        "conda deactivate" and then "source venv/bin/activate", or to install using
        the venv's pip by its full path. The golden rule is that pip install and
        python script.py must run in the same environment.

        A missing environment variable does not raise an error. os.getenv returns
        None silently when a name is not found, so the failure surfaces much later
        and somewhere else. One real example in this project was a typo in the .env
        file where SUPABASE_URL had been written as SUPABSE_URL, missing the letter
        A. The code asked for the correctly spelled name, got None, and the failure
        appeared as the confusing message "supabase_url is required" coming from
        create_client. When a variable seems missing, suspect a typo in either the
        .env file or the code, a .env file sitting in a different folder from where
        the script runs, or a missing load_dotenv call. A quick debug trick is to
        print the variable right after load_dotenv to see whether it is None.

        The error "got an unexpected keyword argument" usually means a parenthesis
        was never closed, not that the argument name is wrong. In this project the
        OpenAI client call was missing its closing bracket, so the next statement,
        which created the Supabase client, was swallowed and read as an argument to
        OpenAI. The error said it got an unexpected keyword argument called
        supabase. The tell is that the so-called argument is something that
        obviously does not belong to that function. In VS Code, clicking next to an
        opening bracket highlights its matching partner, which finds the problem
        instantly.

        Other common errors: a 429 from Gemini means the free tier rate limit was
        hit, so wait about sixty seconds, since the limits are roughly 10 requests
        per minute and 250 per day on the chat model. A dimension error on insert
        means the embedding size and the vector(1536) column disagree. A 422 from
        FastAPI means the JSON body did not match the Pydantic model, so for the ask
        endpoint the body must be exactly {"question": "..."}. "Address already in
        use" means a server is still running on that port, so stop it with Ctrl+C or
        start on a different port. "Could not import module main" means uvicorn was
        run from the wrong folder and cannot see main.py.""",
    },
]
