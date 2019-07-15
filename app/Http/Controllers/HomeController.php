<?php

namespace App\Http\Controllers;

use Auth;

use Carbon\Carbon;
use App\Board;
use App\User;
use App\Notice;

class HomeController extends Controller
{
    public function index()
    {
        if (Auth::check()) {
            $notices = Auth::user()->notices()
                           ->orderBy('created_at', 'desc')->get();
            $boards = Auth::user()->subscriptions()->get();
            return view('notices.index', compact('notices', 'boards'));
        } else {
            $boardCount = Board::count();
            $userCount = User::count();
            $noticeCount = Notice::whereNull('deleted_at')->orWhere('deleted_at', '>', Carbon::now())->count();
            return view('welcome', compact('boardCount', 'userCount', 'noticeCount'));
        }
    }
}
