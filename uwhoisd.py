"""
"""

import diesel


def respond(addr):
    query = diesel.until_eol()
    diesel.send("You sent: [%s]\n" % query.strip())


def main():
    diesel.quickstart(diesel.Service(respond, 1043))


if __name__ == '__main__':
    main()
