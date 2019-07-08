<!DOCTYPE html>
<html lang="{{ str_replace('_', '-', app()->getLocale()) }}">

<head>

  <meta charset="utf-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">

  <meta name="csrf-token" content="{{ csrf_token() }}">

  <title>{{ config('app.name') }}: {{ isset($title) ? $title : '' }}</title>

  <link href="https://fonts.googleapis.com/css?family=Nunito:200,200i,300,300i,400,400i,600,600i,700,700i,800,800i,900,900i" rel="stylesheet">
  <link rel="stylesheet" href="{{ mix('/css/vendor.css') }}">
  <link rel="stylesheet" href="{{ mix('/css/app.css') }}">

</head>

<body id="page-top">

  <!-- Page Wrapper -->
  <div id="wrapper">

    <!-- Sidebar -->
    <ul class="navbar-nav bg-gradient-primary sidebar sidebar-dark accordion" id="accordionSidebar">

      <!-- Sidebar - Brand -->
      <a class="sidebar-brand d-flex align-items-center justify-content-center" href="{{ route('home') }}">
        <div class="sidebar-brand-text mx-3">{{ config('app.name') }}</div>
      </a>

      <!-- Divider -->
      <hr class="sidebar-divider my-0">

      @isset($activeBoard)

        <li class="nav-item {{ Route::is('boards.show') || Route::is('notices.show') ? 'active' : '' }}">
          <a class="nav-link" href="{{ route('boards.show', ['board' => $activeBoard]) }}">
            <i class="fas fa-fw fa-chalkboard"></i><span>Notice Board</span>
          </a>
        </li>
        <li class="nav-item {{ Route::is('boards.details') ? 'active' : '' }}">
          <a class="nav-link" href="{{ route('boards.details', ['board' => $activeBoard]) }}">
            <i class="fas fa-fw fa-info-circle"></i><span>About</span>
          </a>
        </li>
        <li class="nav-item {{ Route::is('boards.committee') ? 'active' : '' }}">
          <a class="nav-link" href="{{ route('boards.committee', ['board' => $activeBoard]) }}">
            <i class="fas fa-fw fa-user-friends"></i><span>Committee</span>
          </a>
        </li>
        <li class="nav-item {{ Route::is('boards.members') ? 'active' : '' }}">
          <a class="nav-link" href="{{ route('boards.members', ['board' => $activeBoard]) }}">
            <i class="fas fa-fw fa-user-friends"></i><span>Members</span>
          </a>
        </li>
        <li class="nav-item {{ Route::is('boards.contact') ? 'active' : '' }}">
          <a class="nav-link" href="{{ route('boards.contact', ['board' => $activeBoard]) }}">
            <i class="fas fa-fw fa-envelope-open"></i><span>Contact</span>
          </a>
        </li>
        @can('create', [\App\Notice::class, $activeBoard])
          <hr class="sidebar-divider">
          <li class="nav-item {{ Route::is('notices.create') ? 'active' : '' }}">
            <a class="nav-link" href="{{ route('notices.create', ['board' => $activeBoard]) }}">
              <i class="fas fa-fw fa-plus"></i><span>Add Notice</span>
            </a>
          </li>
        @endcan
        @can('update', $activeBoard)
          <li class="nav-item {{ Route::is('boards.members.add') ? 'active' : '' }}">
            <a class="nav-link" href="{{ route('boards.members.add', ['board' => $activeBoard]) }}">
              <i class="fas fa-fw fa-plus"></i><span>Add Members</span>
            </a>
          </li>
        @endcan
        @admin($activeBoard)
        @else
          <hr class="sidebar-divider">
          @auth
            @section('subscribe_nav')
              <li class="nav-item">
                <button type="submit" class="nav-link"><i class="fas fa-fw fa-star"></i>Subscribe</button>
              </li>
            @endsection
            @section('unsubscribe_nav')
              <li class="nav-item">
                <button type="submit" class="nav-link"><i class="far fa-fw fa-star"></i>Unsubscribe</button>
              </li>
            @endsection
            @include('macros.subscribe', [ 'subscribe' => 'subscribe_nav', 'unsubscribe' => 'unsubscribe_nav', 'board' => $activeBoard, 'user' => null])
          @else
            <li class="nav-item">
              <a href="{{ route('boards.unsubscribe', ['board' => $activeBoard]) }}" class="nav-link">
                <i class="far fa-fw fa-star"></i><span>Unsubscribe</span>
              </a>
            </li>
          @endauth
        @endadmin

      @else

        <li class="nav-item {{ Route::is('boards.search') ? 'active' : '' }}">
          <a class="nav-link" href="{{ route('boards.search') }}">
            <i class="fas fa-fw fa-search"></i>
            <span>Find Boards</span>
          </a>
        </li>
        @auth
          <li class="nav-item {{ Route::is('boards.create') ? 'active' : '' }}">
            <a class="nav-link" href="{{ route('boards.create') }}">
              <i class="fas fa-fw fa-plus"></i>
              <i class="fas fa-fw fa-chalkboard"></i>
              <span>Create Board</span>
            </a>
          </li>
        @endauth

      @endisset

    </ul>
    <!-- End of Sidebar -->

    <!-- Content Wrapper -->
    <div id="content-wrapper" class="d-flex flex-column">

      <!-- Main Content -->
      <div id="content">

        <!-- Topbar -->
        <nav class="navbar navbar-expand navbar-light bg-white topbar mb-4 static-top shadow">

          <!-- Sidebar Toggle (Topbar) -->
          <button id="sidebarToggleTop" class="btn btn-link d-md-none rounded-circle mr-3">
            <i class="fa fa-bars"></i>
          </button>

          <!-- Topbar Search -->
          <form class="d-none d-sm-inline-block form-inline mr-auto ml-md-3 my-2 my-md-0 mw-100 navbar-search" action="{{ route('boards.search') }}" method="GET">
            <div class="input-group">
              <input type="text" name="q" class="form-control bg-light border-0 small" placeholder="Find board..." aria-label="Search" aria-describedby="basic-addon2">
              <div class="input-group-append">
                <button class="btn btn-primary" type="submit">
                  <i class="fas fa-search fa-sm"></i>
                </button>
              </div>
            </div>
          </form>

          <!-- Topbar Navbar -->
          <ul class="navbar-nav ml-auto">

            <!-- Nav Item - Search Dropdown (Visible Only XS) -->
            <li class="nav-item dropdown no-arrow d-sm-none">
              <a class="nav-link dropdown-toggle" href="#" id="searchDropdown" role="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                <i class="fas fa-search fa-fw"></i>
              </a>
              <!-- Dropdown - Messages -->
              <div class="dropdown-menu dropdown-menu-right p-3 shadow animated--grow-in" aria-labelledby="searchDropdown">
                <form class="form-inline mr-auto w-100 navbar-search" action="{{ route('boards.search') }}" method="GET">
                  <div class="input-group">
                    <input type="text" name="q" class="form-control bg-light border-0 small" placeholder="Find board..." aria-label="Search" aria-describedby="basic-addon2">
                    <div class="input-group-append">
                      <button class="btn btn-primary" type="submit">
                        <i class="fas fa-search fa-sm"></i>
                      </button>
                    </div>
                  </div>
                </form>
              </div>
            </li>

            <!-- Nav Item - User Information -->
            <li class="nav-item dropdown no-arrow">
              <a class="nav-link dropdown-toggle" href="#" id="userDropdown" role="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
              @guest
                <span class="mr-2 d-none d-lg-inline text-gray-600 small">Login / Register</span>
              @else
                <i class="fas fa-user fa-sm fa-fw mr-2 text-gray-400"></i>
                <span class="mr-2 d-none d-lg-inline text-gray-600 small">{{ auth()->user()->name }}</span>
              @endguest
            </a>
              <!-- Dropdown - User Information -->

              <div class="dropdown-menu dropdown-menu-right shadow animated--grow-in" aria-labelledby="userDropdown">
                @guest
                  <a class="dropdown-item" href="{{ route('login') }}">
                    <i class="fas fa-user fa-sm fa-fw mr-2 text-gray-400"></i>
                    Login
                  </a>
                  <a class="dropdown-item" href="{{ route('register') }}">
                    <i class="fas fa-user fa-sm fa-fw mr-2 text-gray-400"></i>
                    Register
                  </a>
                @else
                  <a class="dropdown-item" href="{{ route('accounts.edit') }}">
                    <i class="fas fa-user fa-sm fa-fw mr-2 text-gray-400"></i>
                    My Account
                  </a>
                  <a class="dropdown-item" href="{{ route('logout') }}"
                    onClick="event.preventDefault(); document.getElementById('logout-form').submit();">
                    <i class="fas fa-sign-out-alt fa-sm fa-fw mr-2 text-gray-400"></i>
                    Logout
                  </a>
                  <form id="logout-form" action="{{ route('logout') }}" method="POST" style="display: none;">
                    @csrf
                  </form>
                @endguest
              </div>
            </li>

          </ul>

        </nav>
        <!-- End of Topbar -->

        @include('macros.alert', ['key' => 'success', 'class' => 'success'])
        @include('macros.alert', ['key' => 'error', 'class' => 'danger'])
        @include('macros.alert', ['key' => 'warning', 'class' => 'warning'])
        @include('macros.alert', ['key' => 'info', 'class' => 'info'])

        <!-- Begin Page Content -->
        <div id="app" class="{{ $appContainerClasses ?? 'container-fluid' }}">

          @yield('content')

        </div>
        <!-- /.container-fluid -->

      </div>
      <!-- End of Main Content -->

    </div>
    <!-- End of Content Wrapper -->

  </div>
  <!-- End of Page Wrapper -->

  <!-- Scroll to Top Button-->
  <a class="scroll-to-top rounded" href="#page-top">
    <i class="fas fa-angle-up"></i>
  </a>

  <script src="/js/manifest.js"></script>
  <script src="/js/vendor.js"></script>
  <script src="{{ mix('/js/app.js') }}"></script>

  @yield('pagescripts')

</body>

</html>
