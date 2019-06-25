<?php

namespace App\Http\Controllers;

use Auth;

use Carbon\Carbon;

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
            return view('welcome');
        }
    }
}
