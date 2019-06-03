<!DOCTYPE html>
<html lang="{{ str_replace('_', '-', app()->getLocale()) }}">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">

        <meta name="csrf-token" content="{{ csrf_token() }}">

        <title>{{ config('app.name') }}: {{ isset($title) ? $title : '' }}</title>

        <link rel="stylesheet" href="{{ mix('/css/vendor.css') }}">
        <link rel="stylesheet" href="{{ mix('/css/app.css') }}">

    </head>
    <body>

        <div class="d-flex" id="wrapper">

            <!-- Sidebar -->
            <div class="bg-light border-right" id="sidebar-wrapper">
                <div class="sidebar-heading"><a href="/">Towerboard</a></div>
                <div class="list-group list-group-flush">
                    <a href="{{ route('boards.search') }}" class="list-group-item list-group-item-action bg-light">Find Boards</a>
                    <a href="{{ route('boards.index') }}" class="list-group-item list-group-item-action bg-light">My Boards</a>
                    <a href="#" class="list-group-item list-group-item-action bg-light">My Notices</a>
                </div>
            </div>
            <!-- /#sidebar-wrapper -->

            <!-- Page Content -->
            <div id="page-content-wrapper">

                <nav class="navbar navbar-expand-lg navbar-light bg-light border-bottom">

                    <h1 class="mt-4">{{ isset($title) ? $title : '' }}</h1>

                    <div class="collapse navbar-collapse" id="navbarSupportedContent">
                        <ul class="navbar-nav ml-auto mt-2 mt-lg-0">
                        @guest
                            <li class="nav-item">
                                <a class="nav-link" href="{{ route('login') }}">Login</a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link" href="{{ route('register') }}">Register</a>
                            </li>
                        @else
                            <li class="nav-item">
                                <a class="nav-link" href="{{ route('accounts.edit') }}">Account ({{ Auth::user()->forename }})</a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link"
                                href="{{ route('logout') }}"
                                onClick="event.preventDefault();
                                            document.getElementById('logout-form').submit();">Logout</a>
                                <form id="logout-form" action="{{ route('logout') }}" method="POST" style="display: none;">
                                    @csrf
                                </form>
                            </li>
                        @endguest
                        </ul>
                    </div>
                </nav>

                <div id="app" class="container-fluid">
                    @yield('content')
                </div>
            </div>
            <!-- /#page-content-wrapper -->

        </div>
        <!-- /#wrapper -->

        <script src="/js/manifest.js"></script>
        <script src="/js/vendor.js"></script>
        <script src="{{ mix('/js/app.js') }}"></script>

        @yield('pagescripts')

    </body>
</html>
