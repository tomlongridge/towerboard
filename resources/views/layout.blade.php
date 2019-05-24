<!DOCTYPE html>
<html lang="{{ str_replace('_', '-', app()->getLocale()) }}">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">

        <title>Towerboard</title>

        <link rel="stylesheet" href="{{ mix('/css/app.css') }}">

    </head>
    <body>

        <div class="d-flex" id="wrapper">

            <!-- Sidebar -->
            <div class="bg-light border-right" id="sidebar-wrapper">
            <div class="sidebar-heading"><a href="/">Towerboard</a></div>
            <div class="list-group list-group-flush">
                <a href="/boards" class="list-group-item list-group-item-action bg-light">Boards</a>
            </div>
            </div>
            <!-- /#sidebar-wrapper -->

            <!-- Page Content -->
            <div id="page-content-wrapper">

            <nav class="navbar navbar-expand-lg navbar-light bg-light border-bottom">
                <button class="btn btn-primary" id="menu-toggle">Toggle Menu</button>

                <button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#navbarSupportedContent" aria-controls="navbarSupportedContent" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
                </button>

                <div class="collapse navbar-collapse" id="navbarSupportedContent">
                <ul class="navbar-nav ml-auto mt-2 mt-lg-0">
                    <li class="nav-item active">
                    <a class="nav-link" href="#">Home <span class="sr-only">(current)</span></a>
                    </li>
                    <li class="nav-item">
                    <a class="nav-link" href="#">Link</a>
                    </li>
                    <li class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle" href="#" id="navbarDropdown" role="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                        Dropdown
                    </a>
                    <div class="dropdown-menu dropdown-menu-right" aria-labelledby="navbarDropdown">
                        <a class="dropdown-item" href="#">Action</a>
                        <a class="dropdown-item" href="#">Another action</a>
                        <div class="dropdown-divider"></div>
                        <a class="dropdown-item" href="#">Something else here</a>
                    </div>
                    </li>
                </ul>
                </div>
            </nav>

            <div class="container-fluid">
                @yield('body')
            </div>
            </div>
            <!-- /#page-content-wrapper -->

        </div>
        <!-- /#wrapper -->

        <script src="/js/manifest.js"></script>
        <script src="/js/vendor.js"></script>
        <script src="{{ mix('/js/app.js') }}"></script>

        <!-- Menu Toggle Script -->
        <script>
            $("#menu-toggle").click(function(e) {
            e.preventDefault();
            $("#wrapper").toggleClass("toggled");
            });
        </script>

    </body>
</html>
