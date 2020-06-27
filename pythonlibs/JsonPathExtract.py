from jsonpath_rw import parser
import json


class JsonPathExtract():
    '''
    Operator Description
    $ The root element to query. This starts all path expressions.
    @ The current node being processed by a filter predicate.
    * Wildcard. Available anywhere a name or numeric are required.
    .. Deep scan. Available anywhere a name is required.
    .<name> Dot-notated child
    ['<name>' (, '<name>')] Bracket-notated child or children
    [<number> (, <number>)] Array index or indexes
    [start:end] Array slice operator
    [?(<expression>)] Filter expression. Expression must evaluate to a boolean value
    JsonPath (click link to try) Result
    $.store.book[*].author The authors of all books
    $..author All authors
    $.store.* All things, both books and bicycles
    $.store..price The price of everything
    $..book[2] The third book
    $..book[(@.length-1)] The last book
    $..book[0,1] The first two books
    $..book[:2] All books from index 0 (inclusive) until index 2 (exclusive)
    $..book[1:2] All books from index 1 (inclusive) until index 2 (exclusive)
    $..book[-2:] Last two books
    $..book[2:] Book number two from tail
    $..book[?(@.isbn)] All books with an ISBN number
    $.store.book[?(@.price < 10)] All books in store cheaper than 10
    $..book[?(@.price <= $['expensive'])] All books in store that are not "expensive"
    $..* Give me every thing
    '''

    def json_path_extract(self, json_data, xpath):
        an_expr = parser.parse(xpath)
        get_data = an_expr.find(json.loads(json_data))
        result = [match.value for match in get_data]
        return result


if __name__ == "__main__":
    '''
    For testing purposes.
    '''
    json_content = '''{
  "firstName": "John",
  "lastName" : "doe",
  "age"      : 26,
  "address"  :
  {
    "streetAddress": "naist street",
    "city"         : "Nara",
    "postalCode"   : "630-0192"
  },
  "phoneNumbers":
    {
      "type"  : "iPhone",
      "number": "0123-4567-8888"
    }
}'''
    my_xpath = "$.phoneNumbers.number"
    print JsonPathExtract().json_path_extract(json_content, my_xpath)[0]