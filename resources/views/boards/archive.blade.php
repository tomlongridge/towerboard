@extends('boards.layout', ['title' => 'Edit Notice', 'activeBoard' => $board])

@section('subcontent')

  <div class="card shadow mb-4">
    <div class="card-header py-3">
      <h6 class="m-0 font-weight-bold text-primary">Board Archive</h6>
    </div>
    <div class="card-body">
      @if(!$notices->isEmpty())
        <div class="table-responsive">
          <table class="table table-bordered" id="notice-table" width="100%" cellspacing="0">
            <thead>
              <tr>
                <th>Notice</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              @foreach ($notices as $key => $notice)
                <tr>
                  <td>{{ $notice->title }}</td>
                  <td>{{ \App\Helpers\Utils::dateToStr($notice->created_at) }}</td>
                  <td><a href="{{ route('notices.show', ['board' => $board, 'notice' => $notice]) }}">View</a></td>
                </tr>
              @endforeach
            </tbody>
          </table>
        </div>
      @else
        There are no archived notices.
      @endif
    </div>
  </div>

@endsection

@section('pagescripts')
<script>
  $(document).ready(function() {
    $('#notice-table').DataTable({
        "paging": true,
        "ordering": true,
        "info": false,
        "lengthMenu": [ [25, 50, -1], [25, 50, "All"] ],
        "columns": [
          null,
          null,
          { "orderable": false },
        ]
    });
  });

</script>
@endsection
