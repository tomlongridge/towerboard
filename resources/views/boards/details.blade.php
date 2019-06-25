@extends('boards.layout', ['title' => 'Edit Notice', 'activeBoard' => $board])

@section('subcontent')

  <div class="row d-flex flex-wrap">

    <div class="col-lg-4 d-flex flex-col">
      <div class="card shadow mb-4 w-100">
        <div class="card-header py-3">
          <h6 class="m-0 font-weight-bold text-primary">Website</h6>
        </div>
        <div class="card-body">
          @isset($board->website_url)
            <a href="{{ $board->website_url }}" target="_blank">{{ $board->website_url }}</a>
          @else
            None
          @endisset
        </div>
      </div>
    </div>

    <div class="col-lg-4 d-flex flex-col ">
      <div class="card shadow mb-4 w-100">
        <div class="card-header py-3">
          <h6 class="m-0 font-weight-bold text-primary">Address</h6>
        </div>
        <div class="card-body">
          <p>
            @isset($board->address)
              {{ $board->address }}<br />
            @endisset
            @isset($board->postcode)
              {{ $board->postcode }}
            @endisset
            @if(!isset($board->address) && !isset($board->postcode))
              Unknown
            @endif
          </p>
          @isset($board->longitude)
            <p>
              <a href="https://www.google.com/maps/search/?api=1&query={{ $board->longitude }},{{ $board->latitude }}" target="_blank">View Map</a>
            </p>
          @endisset
        </div>
      </div>
    </div>

    <div class="col-lg-4 d-flex flex-col">
      <div class="card shadow mb-4 w-100">
        <div class="card-header py-3">
          <h6 class="m-0 font-weight-bold text-primary">Map</h6>
        </div>
        @isset($board->latitude)
          <div class="card-body" id="map" style="padding: 0px; height:400px"></div>
        @else
          <div class="card-body">Unknown</div>
        @endisset
      </div>
    </div>
  </div>

  @if(!$board->affiliatedTo->isEmpty())
    <h2>Affiliations</h2>
    <div class="row">
      @foreach($board->affiliatedTo as $affiliate)
        <div class="col-lg-3">
          <div class="card border-left-primary shadow h-100 py-2">
            <div class="card-body">
              <div class="row no-gutters align-items-center">
                <div class="col mr-2">
                  <div class="mb-0 text-gray-800">
                    @include('macros.board', ['board' => $affiliate, 'route' => 'boards.details'])
                  </div>
                </div>
                <div class="col-auto">
                  @include('macros.boardicon', ['board' => $affiliate])
                </div>
              </div>
            </div>
          </div>
        </div>
      @endforeach
    </div>
  @endif

  @if(!$board->affiliates->isEmpty())
    <h2>Affiliated Boards</h2>
    <div class="row">
      @foreach($board->affiliates as $affiliate)
        <div class="col-lg-4">
          <div class="card border-left-primary shadow h-100 py-2">
            <div class="card-body">
              <div class="row no-gutters align-items-center">
                <div class="col mr-2">
                  <div class="mb-0 text-gray-800">
                    @include('macros.board', ['board' => $affiliate, 'route' => 'boards.details', 'full' => false])
                  </div>
                </div>
                <div class="col-auto">
                  @include('macros.boardicon', ['board' => $affiliate])
                </div>
              </div>
            </div>
          </div>
        </div>
      @endforeach
    </div>
  @endif

  @can('update', $board)

    <div class="row px-3 py-2 my-4">

      <a href="{{ route('boards.edit', ['board' => $board->name]) }}" class="btn btn-primary btn-icon-split mr-2">
        <span class="icon text-white-50"><i class="fas fa-edit"></i></span>
        <span class="text">Edit</span>
      </a>

      <form method="POST" action="{{ route('boards.destroy', ['board' => $board->name]) }}" style="display: inline">
          @method("DELETE")
          @csrf
          <button type="submit" class="btn btn-danger btn-icon-split" onclick="return confirm('Are you sure?')">
            <span class="icon text-white-50"><i class="fas fa-trash"></i></span>
            <span class="text">Delete</span>
          </button>
      </form>
    </div>

  @endcan

@endsection

@section('pagescripts')
  @isset($board->latitude)
    <script>
      mapboxgl.accessToken = "{{ env('MAPBOX_API_KEY') }}";
      var map = new mapboxgl.Map({
        container: 'map',
        style: 'mapbox://styles/mapbox/streets-v11',
        center: [{{ $board->latitude }}, {{ $board->longitude }}],
        zoom: 15
      });
      new mapboxgl.Marker().setLngLat([{{ $board->latitude }}, {{ $board->longitude }}]).addTo(map);
    </script>
  @endisset
@endsection
