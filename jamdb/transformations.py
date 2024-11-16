import copy


def id_from_name(name):
    return name.lower().strip().replace(" ", "_")


def format_id_as_str(x):
    # Some ids are strs that look like nums, and pandas will cast them to float.
    # This undoes that.
    try:
        x = float(x)
        x = f"{x:.0f}"
    except ValueError:
        pass
    return x
    

def cleanup_youtube_link(link):
    def _youtube_to_youtu_be(link):
        prefixes = ["https://www.youtube.com", "https://m.youtube.com"]
        for prefix in prefixes:
            if link.startswith(prefix):
                link = link.replace(prefix, "https://youtu.be")
        return link
    link = _youtube_to_youtu_be(link)

    if "?" in link:
        link, params = link.split("?", 1)
        params = params.split("&")

        if link.endswith("/watch"):
            link = link[:-len("watch")]
            uri = [param[2:] for param in params if param.startswith("v=")][0]
            link += uri
        kept_params = [x for x in params if x.startswith("t=")]
        kept_params = "&".join(kept_params)
        if kept_params != "":
            link += f"?{kept_params}"
    return link


def create_embed_link(source, link):
    embed_link = ""
    if source.lower() == "youtube":
        embed_link = _youtube_link_to_embed(link)
    elif source.lower() == "spotify":
        embed_link = _spotify_link_to_embed(link)
    return embed_link


def _youtube_link_to_embed(link):
    embed_pref = "https://youtube.com/embed/"
    for prefix in ["https://youtu.be/", "https://youtube.com/"]:
        if link.startswith(prefix):
            embed_link = link.replace(prefix, embed_pref)
            if "?" in embed_link:
                embed_link, params = embed_link.split("?")
                params = params.split("&")
                for idx, param in enumerate(params):
                    if param.startswith("t="):
                        params[idx] = param.replace("t=", "start=")
                embed_link = embed_link + "?" + "&".join(params)
            return embed_link
    return ""


def _spotify_link_to_embed(link):
    if "embed" in link:
        embed_link = link
    else:
        pattern = "spotify.com/"
        prefix, content = link.split(pattern)
        prefix = f"{prefix}{pattern}embed/"
        embed_link = f"{prefix}{content}"
    return embed_link
