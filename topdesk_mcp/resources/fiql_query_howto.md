# FIQL Query Hints

FIQL (Feed Item Query Language) is a query language that allows you to filter and search for items in TOPdesk.
It uses a simple syntax to specify the criteria for the items you want to retrieve.

## The following operations are available:

* `field==value`: Equals. Not available for memo values.
* `field!=value`: Not equal. Not available for memo values.
* `field==null`: Is null. Special case of Equals, works for all field types.
* `field!=null`: Is not null. Special case of Not equal, works for all field types.
* `field=gt=value`: Greater than. Only available for numeric and date values.
* `field=ge=value`: Greater than or equal. Only available for numeric and date values.
* `field=lt=value`: Less than. Only available for numeric and date values.
* `field=le=value`: Less than or equal. Only available for numeric and date values.
* `field=sw=value`: Starts with. Only available for text and memo values.
* `field=in=(oneValue,otherValue)`: In list. For querying resources that have one of several values, for example all reservations and requests. Not available for memo values.
* `field=out=(oneValue,otherValue)`: Not in list. For querying resources that don't have one of several values, for example all reservations except cancelled and rejected ones. Not available for memo values.
* `oneCondition;otherCondition`: And operation. Conditions can be and-ed together using a `;`.
* `oneCondition,otherCondition`: Or operation. Conditions can be or-ed together using a `,`.
* You can use brackets to group `and`/`or` sets together. By default, `and` takes precedence.

### Values

A `value` can be specified without quoting or escaping, unless it contains a white space or reserved character.

* String values can be quoted using either ' or ".
* If you need to use both single and double quotes inside a quoted argument, then you must escape one of them using \ (backslash).
* If you want to use \ literally, then double it as \\. Backslash has a special meaning only inside a quoted argument, not in unquoted argument.
* The reserved characters are ' " ( ) ; , = ! ~ > >.
* Date values can be specified using ISO 8601 format which is yyyy-MM-ddTHH:mm:ssZ. The time zone can be specified as Z for UTC, or as offset +/-0900 or +/-01:00.

## FIQL query examples for Incidents:

* `creationDate=lt=2014-01-01T00:00:00Z`: All incidents created before 1st January 2014 UTC.
* `modifictionDate=ge=2014-01-01T00:00:00Z;modifictionDate=lt=2014-02-01T00:00:00Z`: All incidents modified between 1st January 2014 and 1st February 2014 UTC.
* `caller.name=='John Doe'`: All incidents where the caller's name is John Doe.
* `operator.name=='Jane Smith'`: All incidents where the operator's name is Jane Smith.
* `operatorGroup.name=in=(Support,HR)`: All incidents where the operator group is either Support or HR.
* 'status=secondLine;impact.name=Department`: All incidents where the status is second line and the impact is Department level.