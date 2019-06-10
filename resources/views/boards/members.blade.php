@extends('boards.layout')

@section('subcontent')

    <h2>Members</h2>

    @admin($board)
        <table>
            <thead>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Action</th>
            </thead>
            <tbody>
                @foreach($board->subscribers as $user)
                    <tr>
                        <td>
                            {{ $user->name }}
                        </td>
                        <td>
                            {{ TowerBoardUtils::obscureEmail($user->email) }}
                        </td>
                        <td>
                            @if($user->id != auth()->id())
                                <form method="POST" action="{{ route('subscriptions.update', ['board' => $board, 'user' => $user]) }}" style="display: inline">
                                    @csrf
                                    @method('PATCH')
                                    <select name="type" onchange="this.form.submit()">
                                        @foreach (\App\Enums\SubscriptionType::getInstances() as $type)
                                            <option
                                                value="{{ $type->value }}"
                                                {{ $type->key == $user->subscription->type->key ? 'selected' : ''}}>
                                                {{ $type->description }}
                                            </option>
                                        @endforeach
                                    </select>
                                </form>
                            @endif
                        </td>
                        <td>
                            @section('inline-unsubscribe')
                                <input type="submit" class="btn btn-primary" value="Remove" />
                            @endsection
                            @include('macros.subscribe', [ 'unsubscribe' => 'inline-unsubscribe', 'board' => $board, 'user' => $user ])
                        </td>
                    </li>
                @endforeach
            </tbody>
        </table>
    @else
        <p>{{ $board->subscribers->count() }} members on Towerboard.</p>
    @endif

    <h2>Board Administrators</h2>
    <ul>
        @foreach($board->administrators()->get() as $admin)
            <li>{{ $admin->name }}</li>
        @endforeach
    </ul>

    @can('update', $board)
        <h2>Add Users</h2>
        <form method="POST" action="{{ route('subscriptions.email', ['board' => $board->name]) }}">
            @csrf
            <textarea name="emails" class="form-control">{{ old('emails') }}</textarea>
            <button type="submit" class="btn btn-primary">Add</button>
        </form>
    @endcan

    @if(!$errors->isEmpty())
        <ul class="alert alert-danger">
        @foreach($errors->all() as $error)
            <li>{{ $error }}</li>
        @endforeach
        </ul>
    @endif

@endsection
