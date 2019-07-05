@extends('boards.layout', ['title' => 'Edit Notice', 'activeBoard' => $board])

@section('subcontent')

  <div class="card shadow mb-4">
    <div class="card-header py-3">
      <h6 class="m-0 font-weight-bold text-primary">Committee</h6>
    </div>
    <div class="card-body">
      @if(!$committee->isEmpty())
        <div class="table-responsive">
          <table class="table table-bordered" id="member-table" width="100%" cellspacing="0">
            <thead>
              <tr>
                <th>Name</th>
                <th>Role</th>
                @if($board->isAdmin() || $board->isCommittee())
                  <th>Contact List</th>
                @endif
                @admin($board)
                  <th>Action</th>
                @endadmin
              </tr>
            </thead>
            <tbody>
              @foreach($committee as $role)
                <tr>
                  <td width="50%">{{ $role->name ?? $role->user->name }}</td>
                  <td>
                    @admin($board)
                      @if($role->user_id != auth()->id())
                          <form method="POST" action="{{ route('roles.update', ['board' => $board, 'role' => $role->id]) }}" style="display: inline">
                              @csrf
                              @method('PATCH')
                              <input type="hidden" name="contactable" value="{{ $role->contactable }}" />
                              <select name="type" class="form-control" onchange="this.form.submit()">
                                  @foreach (\App\Enums\RoleType::getInstances() as $type)
                                    @if ($type->value != \App\Enums\RoleType::NONE)
                                      <option
                                          value="{{ $type->value }}"
                                          {{ $type->key == $role->type->key ? 'selected' : ''}}>
                                          {{ ucwords($type->description) }}
                                      </option>
                                    @endif
                                  @endforeach
                              </select>
                          </form>
                      @endif
                    @else
                      {{ ucwords($role->type->description) }}
                    @endadmin
                  </td>
                    @if($board->isAdmin() || $board->isCommittee())
                      <td>
                        <form method="POST" action="{{ route('roles.update', ['board' => $board->name, 'role' => $role->id]) }}" style="display: inline">
                            @method("PATCH")
                            @csrf
                            <input type="hidden" name="type" value="{{ $role->type->value }}" />
                            <input type="hidden" name="contactable" value="{{ $role->contactable ? '0' : '1' }}" />
                            <input type="checkbox" onclick="this.form.submit()" value=""
                                   @if($role->contactable) checked @endif
                                   @if(!$board->isAdmin() && $role->user && $role->user->id != auth()->id()) disabled @endif />
                        </form>
                      </td>
                    @endif
                    @admin($board)
                      <td>
                        <form method="POST" action="{{ route('roles.destroy', ['board' => $board->name, 'role' => $role->id]) }}" style="display: inline">
                            @method("DELETE")
                            @csrf
                            <button type="submit" class="btn btn-danger btn-icon-split">
                              <span class="icon text-white-50"><i class="fas fa-trash"></i></span>
                              <span class="text">Remove</span>
                            </button>
                        </form>
                      </td>
                    @endadmin
                </tr>
              @endforeach
            </tbody>
          </table>
        </div>
      @else
        There are no members/subscribers.
      @endif
    </div>
  </div>

  @admin($board)
    <div class="card shadow mb-4">
      <div class="card-header py-3">
        <h6 class="m-0 font-weight-bold text-primary">Add Member</h6>
      </div>
      <div class="card-body">
        <div class="table-responsive">
          <form method="POST" id="add-form" action="{{ route('roles.store', ['board' => $board]) }}" novalidate>
            @csrf
            <table class="table table-bordered" width="100%" cellspacing="0">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Role</th>
                  <th>Contact List</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td width="50%">
                    <div class="form-group">
                        <select id="name-select" class="tb-dropdown" required>
                          <option></option>
                          @foreach ($board->members()->get() as $member)
                            <option value="{{ $member->id }}">{{ $member->name }}</option>
                          @endforeach
                        </select>
                        <input type="hidden" name="name" id="name-hidden" value="" />
                        <input type="hidden" name="user_id" id="userid-hidden" value="" />
                        <div class="invalid-feedback">@error('name') {{ $message }} @else Please enter the name of the committee member. @enderror</div>
                    </div>
                  </td>
                  <td>
                      <select name="type" class="form-control">
                          @foreach (\App\Enums\RoleType::getInstances() as $type)
                            @if ($type->value != \App\Enums\RoleType::NONE)
                              <option
                                  value="{{ $type->value }}"
                                  {{ old('type', \App\Enums\RoleType::getInstance(\App\Enums\RoleType::CORRESPONDENT)) == $type ? 'selected' : '' }} >
                                  {{ ucwords($type->description) }}
                              </option>
                            @endif
                          @endforeach
                      </select>
                  </td>
                  <td>
                      <input type="checkbox" name="contactable" value="1" @if(old('contactable')) checked @endif />
                  </td>
                  <td>
                    <button type="submit" class="btn btn-success btn-icon-split">
                      <span class="icon text-white-50"><i class="fas fa-plus"></i></span>
                      <span class="text">Add</span>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </form>
        </div>
      </div>
    </div>
  @endadmin

@endsection

@section('pagescripts')
<script>
  $(document).ready(function() {
    $('#member-table').DataTable({
        "paging": false,
        "ordering": true,
        "info": false,
        "searching": false,
        "columns": [
          null,
          @admin($board)
            { "orderable": false },
          @else
            null,
          @endadmin
          @if($board->isAdmin() || $board->isCommittee())
            { "orderable": false },
          @endif
          @admin($board)
            { "orderable": false },
          @endadmin
        ]
    });
  });

  $('#add-form').on('submit', function(event) {
    if (this.checkValidity() === false) {
      event.preventDefault();
      event.stopPropagation();
    }
    this.classList.add('was-validated');
  });

  $('#name-select').selectize({
    create: true,
    persist: false,
    placeholder: 'Type name of member...',
    selectOnTab: true,
    dropdownParent: "body",
    render: {
      option_create: function(data, escape) {
       return '<div class="create" style="padding: 10px"><strong> ' + escape(data.input) + '</strong> is not a member. Click here to use name only.</div>';
      }
    },
    onChange: function(value) {
      if($.isNumeric(value)) {
        $('#userid-hidden').val(value);
        $('#name-hidden').val();
      } else {
        $('#name-hidden').val(value);
        $('#userid-hidden').val();
      }
    }
  });
</script>
@endsection
