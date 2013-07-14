var body_padding = 130;
var search_index = [];

function update_search_suggest()
{
    var search_val = $('#search_bar').val();
    var words = search_val.split(" ");

    var str = words[ words.length - 1 ];

    var terms = [];

    for (var i=0; i<search_index.length; i++)
    {
      if (search_index[i].substring(0, str.length).toLowerCase() === str.toLowerCase())
      {
        if (terms.length < 4)
        {
          terms.push(search_index[i])
        }
        else
        {
          break;
        }
      }
    }

    $('#search_suggest').children(':first-child').html('');

    for (var i=0; i<terms.length; i++)
    {
      $('#search_suggest').children(':first-child').append('<tr class="s_suggest"><td onmousedown="set_search_val(this);">' + terms[i] +'</td></tr>');
    }
}

$(document).ready( function() {
  
  $.get( '/Scripts/get_tags', function(data) {
    search_index = json_parse(data);
  });

  $('#search_suggest').css('left', $('#search_bar').offset().left);
  $('#search_suggest').css('top', $('#search_bar').offset().top + $('#search_bar').outerHeight());
  $('#search_suggest').css('width', $('#search_bar').width());
  $('#search_suggest').css('display', 'none');
  //$('#search_suggest').css('height', $('#search_bar').outerHeight());

  $('#search_bar').keyup( update_search_suggest );

  $('#search_bar').blur( function() { 
    setTimeout( function() {
      $('#search_suggest').css('display', 'none');
      $('#search_bar').keypress();
      }, 100 );
  }); 

  $('#search_bar').focus( function() { 
    $('#search_suggest').css('display', 'inline-block');
    $('#search_suggest').css('left', $('#search_bar').offset().left);
    $('#search_suggest').css('top', $('#search_bar').offset().top + $('#search_bar').outerHeight());
    update_search_suggest();
  });  

});

function set_search_val(element)
{
  var value = $('#search_bar').val();
  var words = value.split(" ");

  var new_word = $(element).html();
  words[ words.length - 1 ] = new_word;

  $('#search_bar').attr( 'value', words.join(" ") );
}

function init()
{
  var bottom_buffer = 15;
  document.getElementById('content').style.height = Number(document.body.clientHeight) - body_padding - Number(document.getElementById('menu_bar').offsetHeight) - (Number(document.getElementById('content').offsetHeight)*2) - bottom_buffer; 
//Sets content height to remaining screen height including a buffer

  sec_home(); //Sets home information on the secondary menu

  SyntaxHighlighter.autoloader(
    'js jscript javascript  /JS/BrushScript/shBrushJScript.js',
    'applescript            /JS/BrushScript/shBrushAppleScript.js',
    'applescript            /JS/BrushScript/shBrushAppleScript.js',
    'actionscript3 as3      /JS/BrushScript/shBrushAS3.js',
    'bash shell             /JS/BrushScript/shBrushBash.js',
    'coldfusion cf          /JS/BrushScript/shBrushColdFusion.js',
    'cpp c                  /JS/BrushScript/shBrushCpp.js',
    'c# c-sharp csharp      /JS/BrushScript/shBrushCSharp.js',
    'css                    /JS/BrushScript/shBrushCss.js',
    'delphi pascal          /JS/BrushScript/shBrushDelphi.js',
    'diff patch pas         /JS/BrushScript/shBrushDiff.js',
    'erl erlang             /JS/BrushScript/shBrushErlang.js',
    'groovy                 /JS/BrushScript/shBrushGroovy.js',
    'java                   /JS/BrushScript/shBrushJava.js',
    'jfx javafx             /JS/BrushScript/shBrushJavaFX.js',
    'js jscript javascript  /JS/BrushScript/shBrushJScript.js',
    'perl pl                /JS/BrushScript/shBrushPerl.js',
    'php                    /JS/BrushScript/shBrushPhp.js',
    'text plain             /JS/BrushScript/shBrushPlain.js',
    'py python              /JS/BrushScript/shBrushPython.js',
    'ruby rails ror rb      /JS/BrushScript/shBrushRuby.js',
    'sass scss              /JS/BrushScript/shBrushSass.js',
    'scala                  /JS/BrushScript/shBrushScala.js',
    'sql                    /JS/BrushScript/shBrushSql.js',
    'vb vbnet               /JS/BrushScript/shBrushVb.js',
    'xml xhtml xslt html    /JS/BrushScript/shBrushXml.js'
  );

  SyntaxHighlighter.all();
}

function stringToDom(s)
{
	var div = document.createElement('div');
	div.innerHTML = s;

	return div.firstChild;
}

function format_print()
{
  $('#sec_menu').css('display', 'none');
  $('#widgets').css('display', 'none');

  $('#content').attr( 'height_bu', $('#content').css('height') );

  $('#content').css('width', 'auto');
  $('#content').css('height', 'auto');
  $('#content').css('overflow-y', 'auto');

  document.getElementById('content_expand').onclick = unformat_print;
  document.getElementById('content_expand').src = '/IMG/Remove_Item_List.png';
}

function unformat_print()
{
  $('#sec_menu').css('display', 'block');
  $('#widgets').css('display', 'block');

  $('#content').css( 'width', '63%' );
  $('#content').css( 'height', $('#content').attr('height_bu') );
  $('#content').css( 'overflow-y', 'scroll' );

  document.getElementById('content_expand').onclick = format_print;
  document.getElementById('content_expand').src = '/IMG/Add_Item_List.png';
}

function select_option(element, value)
{
	for (var i=0; i<element.options.length; i++)
	{
		if (element.options[i].value == value)
		{
			element.selectedIndex = i;
			break;
		}
	}

}

function get_citation(id, location)
{
	$.get( "/Scripts/get_citation_html?p="+location, function(data) {
		document.getElementById(id).innerHTML = data;
	})
	.error( function() {
		document.getElementById(id).innerHTML = "Failed to load citation.";
	});
}

function get_calendar(id, year, month, searchText)
{
	if (searchText === undefined)
	{
		searchText = "";
	}

	$.get( "/Scripts/get_calendar_html?year="+year+"&month="+month+"&search="+searchText, function(data) {
		document.getElementById(id).innerHTML = data;
	})
	.error( function() {
		document.getElementById(id).innerHTML = "Failed to load calendar.";
	});
}

//All sec_* functions alter the content of the secondary menu bar
function sec_about()
{
	$.get( "/navigation/spi_about", function(data) {
		document.getElementById('sec_menu').innerHTML = data;
	});
}

function home()
{
//Sets main content to home section
	$.get( "/home_content", function(data) {
		document.getElementById('content').innerHTML = data;
	});
}

function sec_home()
{
//Sets home info on the secondary
	$.get( "/navigation/spi_home", function(data) {
		document.getElementById('sec_menu').innerHTML = data;
	});
}

function sec_missions()
{
//  Links to each project on the secondary
//  Projects are sent with their relative url and name in pairs, csv
	$.get( "/Scripts/get_visible_projects", function(data) {
		var sec_menu = document.getElementById('sec_menu');
		var projects = data.split(',');

		sec_menu.innerHTML = '<h2>Missions</h2><ul>';
		for(var i=1; i < projects.length; i += 2)
		{
			sec_menu.innerHTML += '<li><a href="' + projects[i-1] + '">' + projects[i] + '</a></li>';
		}
		sec_menu.innerHTML += '</ul>';
	});
}

function sec_users()
{
//Links to each user on the secondary
	$.get( "/Scripts/get_users", function(data) {
		var sec_menu = document.getElementById('sec_menu');
		var users = data.split(',');

		sec_menu.innerHTML = '<h2>SPIes</h2><ul>';
		for(var i=0; i < users.length; i++)
		{
			sec_menu.innerHTML += '<li><a href="/Users/' + users[i] + '/blog">' + users[i] + '</a></li>';
		}
		sec_menu.innerHTML += '</ul>';
	});
}

function sec_docs()
{
//Links to docs on the secondary
	$.get( "/navigation/spi_docs", function(data) {
		document.getElementById('sec_menu').innerHTML = data;
	});
}

function sec_tools()
{
//Links to tools on the secondary
	$.get( "/navigation/spi_tools", function(data) {
		document.getElementById('sec_menu').innerHTML = data;
	});
}

function sec_contact()
{
//Contact info on the secondary
	$.get( "/navigation/spi_contact", function(data) {
		document.getElementById('sec_menu').innerHTML = data;
	});
}


