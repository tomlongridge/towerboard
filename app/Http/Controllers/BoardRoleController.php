<?php

namespace App\Http\Controllers;

use App\Board;
use App\BoardRole;
use App\Enums\RoleType;
use Illuminate\Http\Request;
use BenSampo\Enum\Rules\EnumValue;
use BenSampo\Enum\Traits\CastsEnums;
use Illuminate\Support\Facades\Validator;

class BoardRoleController extends Controller
{
    use CastsEnums;

    protected $enumCasts = [
        'type' => RoleType::class
    ];

    /**
     * Display a listing of the resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function index(Board $board)
    {
        return redirect(route("boards.committee", ['board' => $board->name]));
    }

    /**
     * Show the form for creating a new resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function create(Board $board)
    {
        return redirect(route("boards.committee", ['board' => $board->name]));
    }

    /**
     * Store a newly created resource in storage.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return \Illuminate\Http\Response
     */
    public function store(Request $request, Board $board)
    {
        $this->authorize('create', [BoardRole::class, $board]);

        $validator = Validator::make($request->all(), [
            'name' => 'required_without:user_id',
            'user_id' => 'nullable|required_without:name|exists:users,id',
            'contactable' => 'sometimes|boolean'
        ]);

        if ($validator->fails()) {
            return redirect(route('boards.committee', ['board' => $board->name]))
                        ->withErrors($validator)
                        ->withInput();
        }

        BoardRole::create($request->merge([
            'board_id' => $board->id,
            'type' => RoleType::getInstance(intval($request->type))
        ])->all());

        return redirect(route('boards.committee', ['board' => $board->name]));
    }

    /**
     * Show the form for editing the specified resource.
     *
     * @param  \App\Notice  $notice
     * @return \Illuminate\Http\Response
     */
    public function edit(Board $board, Notice $notice)
    {
        return redirect(route("boards.committee", ['board' => $board->name]));
    }

    /**
     * Update the specified resource in storage.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  \App\BoardRole  $boardRole
     * @return \Illuminate\Http\Response
     */
    public function update(Request $request, Board $board, BoardRole $role)
    {
        $validator = Validator::make($request->all(), [
            'contactable' => 'boolean',
            'type' => 'numeric'
        ]);

        if ($validator->fails()) {
            return response('Bad Request', 400);
        }

        $this->authorize('update', [$board, BoardRole::class]);

        $role->update([
            'contactable' => $request->contactable,
            'type' => RoleType::getInstance(intval($request->type))
        ]);

        return redirect(route('boards.committee', ['board' => $board->name]));
    }

    /**
     * Remove the specified resource from storage.
     *
     * @param  \App\BoardRole  $boardRole
     * @return \Illuminate\Http\Response
     */
    public function destroy(Request $request, Board $board, BoardRole $role)
    {
        $this->authorize('delete', [$board, $role]);

        $role->delete();

        return redirect(route('boards.committee', ['board' => $board->name]));
    }
}
