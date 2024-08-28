<!doctype html>
<html lang="en">

<head>
  <!-- Required meta tags -->
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
  <meta name="Description" content="Web frontend for gallery-dl">

  <title>gallery-dl</title>
  
  <style type="text/css">
  .flash-red {
    border: 1px solid red; 
    border-radius: 5px;
    padding: 3px;
    background-color: pink; 
    color: red;
  }
  .flash-green {
    border: 1px solid green; 
    border-radius: 5px;
    padding: 3px;
    background-color: lightgreen; 
    color: green;
  }
  textarea {
    width: 80%;
    height: 16ex;
  }
  
table.greyGridTable {
  border: 2px solid #FFFFFF;
  #width: 100%;
  text-align: center;
  border-collapse: collapse;
}
table.greyGridTable td, table.greyGridTable th {
  border-bottom: 1px solid #000000;
  padding: 3px 4px;
}
table.greyGridTable tbody td {
  font-size: 13px;
}
table.greyGridTable td:nth-child(even) {
  background: #EBEBEB;
}
table.greyGridTable thead {
  background: #FFFFFF;
  border-bottom: 4px solid #333333;
}
table.greyGridTable thead th {
  font-size: 15px;
  font-weight: bold;
  color: #333333;
  text-align: center;
  border-left: 2px solid #333333;
}
table.greyGridTable thead th:first-child {
  border-left: none;
}

table.greyGridTable tfoot {
  font-size: 14px;
  font-weight: bold;
  color: #333333;
  border-top: 4px solid #333333;
}
table.greyGridTable tfoot td {
  font-size: 14px;
}
  </style>
</head>

<body>
  <div class="container d-flex flex-column text-light text-center">
    <div class="flex-grow-1"></div>
    <div class="jumbotron bg-transparent flex-grow-1">
      <h1 class="display-4"><a href="/">gallery-dl</a></h1>
      <div class="{{flashclass}}">{{flash}}</div>
      <p class="lead">Enter a url to download the photos to the server. Url can be to <a class="text-info"
          href="https://github.com/mikf/gallery-dl/blob/master/docs/supportedsites.md">any
          other supported site</a>.</p>
      <p class="lead">For links that should be handled by yt-dlp, prepend "ytdl:" before the Url. Url can be to <a class="text-info"
          href="https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md">any
          other supported site</a>.</p>
      
      
      <hr class="my-4">
      <div>
        <form action="/" method="POST">
          <div class="input-group">
            <textarea name="url" type="url" class="form-control" placeholder="URLS" aria-label="URL" aria-describedby="button-submit" autofocus></textarea>
            <div class="input-group-append">
              <button class="btn btn-primary" type="submit" id="button-submit">Submit</button>
            </div>
          </div>
        </form>
      </div>
    </div>
</br>
    <div>
        <h3>Queue</h3>
        <table class="greyGridTable">
        <tr><th>ID</th><th>url</th><th>status</th><th>enqueued</th><th>started</th><th>finished</th><th>path</th><th>size</th><th colspan=2>Actions</th></tr>
        %for entry in queue:
        <tr>
          %for elm in entry:
<td>{{elm}}</td>\\
          %end
          <td><a href="/delete/{{entry[0]}}">Delete</a></td><td><a href="/restart/{{entry[0]}}">Restart</a></td>
        %end
        </table>
        There are currently {{queue_length}} elements waiting to be downloaded.
        <!--<a href="/gallery-dl/create_zip">Click here to create zip.</a>-->
    </div>
    <footer>
      <div>
        <p class="text-muted">Web frontend for <a class="text-light" href="https://github.com/mikf/gallery-dl/">gallery-dl</a></p>
      </div>
    </footer>
  </div>

</body>

</html>
