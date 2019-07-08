 @extends('layouts.app', ['title' => 'Welcome!'])

@section('content')

  <h1 class="h3 mb-0 text-gray-800">Welcome to Towerboard &mdash; the virtual notice board for bell ringers</h1>

  <div class="row align-items-center justify-content-center">

    <div class="col-xl-8 col-lg-7 mt-4">
      <div class="card shadow">
        <div class="card-header py-3 d-flex flex-row align-items-center justify-content-between">
          <h6 class="m-0 font-weight-bold text-primary">For ringers&hellip;</h6>
        </div>
        <div class="card-body">
          <ul>
            <li>Use Towerboard to see notices from towers or groups that you belong to.</li>
            <li>Subscribe to boards to receive notices via email.</li>
            <li>Check notices and send a message to towers that you are visiting.</li>
          </ul>
          <div class="float-right">
            <a href="{{ route('boards.search') }}" class="btn btn-success btn-icon-split">
              <span class="text">Find boards</span>
              <span class="icon text-white-50"><i class="fas fa-arrow-right"></i></span>
            </a>
          </div>
        </div>
      </div>
    </div>

  </div>

  <div class="row align-items-center justify-content-center">

    <div class="col-xl-8 col-lg-7 mt-4">
      <div class="card shadow">
        <div class="card-header py-3 d-flex flex-row align-items-center justify-content-between">
          <h6 class="m-0 font-weight-bold text-primary">For tower masters, correspondents and committee members&hellip;</h6>
        </div>
        <div class="card-body">
          <ul>
            <li>Post notices on your own board for the public to see.</li>
            <li>Notices will be emailed to members of your tower or organisation&hellip;</li>
            <li>&hellip; as well as other people who have subscribed.</li>
            <li>Receive messages from guests through the website to members of the commitee without exposing your email address.</li>
          </ul>
          <div class="float-right">
            @guest
              <a href="{{ route('register') }}" class="btn btn-success btn-icon-split">
                <span class="text">Register</span>
                <span class="icon text-white-50"><i class="fas fa-arrow-right"></i></span>
              </a>
            @else
              <a href="{{ route('boards.create') }}" class="btn btn-success btn-icon-split">
                <span class="text">Create a board</span>
                <span class="icon text-white-50"><i class="fas fa-arrow-right"></i></span>
              </a>
            @endguest
          </div>
        </div>
      </div>
    </div>

  </div>

  <div class="row align-items-center justify-content-center">

      <div class="col-xl-3 col-md-6 mt-4">
        <div class="card border-left-warning shadow h-100 py-2">
          <div class="card-body">
            <div class="row no-gutters align-items-center">
              <div class="col mr-2">
                <div class="text-xs font-weight-bold text-warning text-uppercase mb-1">Boards</div>
                <div class="h5 mb-0 font-weight-bold text-gray-800">{{ $boardCount }}</div>
              </div>
              <div class="col-auto">
                <i class="fas fa-chalkboard fa-2x text-gray-300"></i>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="col-xl-3 col-md-6 mt-4">
        <div class="card border-left-success shadow h-100 py-2">
          <div class="card-body">
            <div class="row no-gutters align-items-center">
              <div class="col mr-2">
                <div class="text-xs font-weight-bold text-success text-uppercase mb-1">Active Notices</div>
                <div class="h5 mb-0 font-weight-bold text-gray-800">{{ $noticeCount }}</div>
              </div>
              <div class="col-auto">
                <i class="fas fa-thumbtack fa-2x text-gray-300"></i>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="col-xl-3 col-md-6 mt-4">
        <div class="card border-left-primary shadow h-100 py-2">
          <div class="card-body">
            <div class="row no-gutters align-items-center">
              <div class="col mr-2">
                <div class="text-xs font-weight-bold text-primary text-uppercase mb-1">Users</div>
                <div class="h5 mb-0 font-weight-bold text-gray-800">{{ $userCount }}</div>
              </div>
              <div class="col-auto">
                <i class="fas fa-user fa-2x text-gray-300"></i>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>

@endsection
